# -*- coding: utf-8 -*-
"""Tablo 4th Gen API client.

Kodi-independent so it can be tested outside Kodi.

Cloud auth flow and HMAC-MD5 device signing are based on the MIT-licensed
tablo-api (trevor-viljoen) and tablo2plex (hearhellacopters) projects.
Recording / scheduling paths follow the legacy local API (jessedp's unofficial
docs), which 4th Gen firmware still serves on port 8885 behind the signed
Authorization header.
"""

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from email.utils import formatdate
from urllib.parse import urlparse

import requests

CLOUD = "https://lighthousetv.ewscloud.com"
CLOUD_UA = "Tablo-FAST/2.0.0 (Mobile; iPhone; iOS 16.6)"
LOCAL_UA = "Tablo-FAST/1.7.0 (Mobile; iPhone; iOS 18.4)"

# Static keys embedded in the official Tablo app (not secrets; see tablo-api README).
HASH_KEY = "6l8jU5N43cEilqItmT3U2M2PFM3qPziilXqau9ys"
DEVICE_KEY = "ljpg6ZkwShVv8aI12E2LP55Ep8vq1uYDPvX0DdTB"


def _mask(email):
    """j***@e***.com — keeps logs shareable."""
    try:
        user, dom = email.split("@", 1)
        host, _, tld = dom.rpartition(".")
        return "{}***@{}***.{}".format(user[:1], host[:1], tld)
    except ValueError:
        return "***"


# Kodi skins are dark, so prefer the logo versions made for dark backgrounds (colour on dark),
# then larger before smaller, then whatever exists.
LOGO_PREFERENCE = ("darkLarge", "darkMedium", "dark", "darkSmall",
                   "lightLarge", "lightMedium", "light", "lightSmall")
LOGO_KINDS_SEEN = set()


def pick_logo(logos):
    by_kind = {}
    for lg in logos:
        if lg.get("url"):
            by_kind.setdefault(lg.get("kind") or "", lg["url"])
            LOGO_KINDS_SEEN.add(lg.get("kind") or "?")
    for kind in LOGO_PREFERENCE:
        if kind in by_kind:
            return by_kind[kind]
    for kind, url in by_kind.items():
        if kind.lower().startswith("dark"):
            return url
    return next(iter(by_kind.values()), "")


class TabloError(Exception):
    pass


class AuthError(TabloError):
    pass


def sign(method, path, body, date):
    """Return the Authorization header value for a local device request."""
    body_hash = hashlib.md5(body.encode("utf-8")).hexdigest() if body else ""
    payload = "{}\n{}\n{}\n{}".format(method, path, body_hash, date)
    sig = hmac.new(HASH_KEY.encode(), payload.encode("utf-8"), hashlib.md5).hexdigest()
    return "tablo:{}:{}".format(DEVICE_KEY, sig)


def _watch_body(client_id):
    return json.dumps({
        "bandwidth": None,
        "extra": {
            "limitedAdTracking": 1,
            "deviceOSVersion": "16.6",
            "lang": "en_US",
            "height": 1080,
            "deviceId": "00000000-0000-0000-0000-000000000000",
            "width": 1920,
            "deviceModel": "iPhone10,1",
            "deviceMake": "Apple",
            "deviceOS": "iOS",
        },
        "device_id": client_id,
        "platform": "ios",
    })


class Tablo(object):
    """One Tablo device, authenticated through the account's cloud login.

    ``state_file`` persists tokens, the device URL and a stable client id so
    Kodi doesn't log in on every plugin invocation.
    """

    def __init__(self, email, password, state_file, device_url_override="",
                 device_name="", timeout=(4, 20), logger=None):
        self.email = email
        self.password = password
        self.state_file = state_file
        self.override = (device_url_override or "").strip().rstrip("/")
        self.device_name = device_name
        self.timeout = timeout
        self.logger = logger or (lambda m: None)
        self.s = requests.Session()
        self._lock = threading.Lock()
        self.state = self._load()
        if self.state.get("email") and self.state.get("email") != email:
            # Different account: keep only the client id.
            self.state = {"client_id": self.state.get("client_id")}
            self._save()
        if not self.state.get("client_id"):
            self.state["client_id"] = str(uuid.uuid4())
            self._save()

    # ------------------------------------------------------------------ state
    def _load(self):
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except (IOError, OSError, ValueError):
            return {}

    def _save(self):
        d = os.path.dirname(self.state_file)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        tmp = self.state_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f)
        os.replace(tmp, self.state_file)

    @property
    def device_url(self):
        if self.override:
            u = self.override
            if "://" not in u:
                u = "http://" + u
            if u.count(":") < 2:
                # Bare IP: keep the port the cloud reports (8887 on current 4th Gen firmware).
                cloud_port = urlparse(self.state.get("device_url", "")).port
                u += ":{}".format(cloud_port or 8887)
            return u
        return self.state.get("device_url", "")

    @property
    def logged_in(self):
        return bool(self.state.get("lighthouse") and self.device_url)

    # ------------------------------------------------------------------ cloud
    def login(self):
        """Full cloud login: credentials -> account -> device-scoped token."""
        if not self.email or not self.password:
            raise AuthError("Enter your Tablo account email and password in settings.")
        with self._lock:
            try:
                return self._login()
            except requests.RequestException as e:
                self.logger("login failed: {}".format(e))
                raise AuthError("Can't sign in to Tablo: {}".format(e))

    def _login(self):
        self.logger("signing in to Tablo cloud as {}".format(_mask(self.email)))
        h = {"User-Agent": CLOUD_UA, "Accept": "*/*"}
        r = self.s.post(CLOUD + "/api/v2/login/",
                        json={"email": self.email, "password": self.password},
                        headers=h, timeout=self.timeout)
        try:
            j = r.json()
        except ValueError:
            j = {}
        if not r.ok or "access_token" not in j:
            raise AuthError("Tablo login failed: {}".format(
                j.get("message") or r.status_code))
        auth = "{} {}".format(j.get("token_type", "Bearer"), j["access_token"])

        r = self.s.get(CLOUD + "/api/v2/account/",
                       headers=dict(h, Authorization=auth), timeout=self.timeout)
        r.raise_for_status()
        acct = r.json()
        profiles = acct.get("profiles") or []
        devices = acct.get("devices") or []
        if not profiles or not devices:
            raise AuthError("No Tablo profiles or devices on this account.")
        dev = devices[0]
        if self.device_name:
            for d in devices:
                if d.get("name", "").lower() == self.device_name.lower():
                    dev = d
                    break

        r = self.s.post(CLOUD + "/api/v2/account/select/",
                        json={"pid": profiles[0]["identifier"], "sid": dev["serverId"]},
                        headers=dict(h, Authorization=auth), timeout=self.timeout)
        r.raise_for_status()
        self.state.update({
            "auth": auth,
            "lighthouse": r.json()["token"],
            "device_url": dev.get("url", "").rstrip("/"),
            "device_name": dev.get("name", ""),
            "sid": dev.get("serverId", ""),
            "login_time": int(time.time()),
            "email": self.email,
        })
        self._find_port()
        self._save()
        self.logger("signed in; device {} at {}".format(
            self.state["device_name"], self.device_url))
        return self.state

    PORTS = (8887, 8885, 80)

    def probe(self, base, timeout=2):
        """True if a Tablo answers the unauthenticated /ping at base."""
        try:
            r = self.s.get(base + "/ping", timeout=timeout)
            self.logger("probe {}/ping -> {}".format(base, r.status_code))
            return r.status_code < 500
        except requests.RequestException as e:
            self.logger("probe {}/ping failed: {}".format(base, e.__class__.__name__))
            return False

    def auth_ok(self, base, timeout=2):
        """True if the Tablo at base accepts a signed request (ping alone isn't enough:
        several ports answer /ping but only the API port accepts the signature)."""
        date = formatdate(usegmt=True)
        try:
            r = self.s.get(base + "/server/info", timeout=timeout, headers={
                "Authorization": sign("GET", "/server/info", "", date), "Date": date,
                "User-Agent": LOCAL_UA, "Accept": "*/*"})
            self.logger("auth check {} -> {}".format(base, r.status_code))
            return r.ok
        except requests.RequestException as e:
            self.logger("auth check {} failed: {}".format(base, e.__class__.__name__))
            return False

    def _find_port(self):
        """The cloud's advertised address isn't always one the Tablo accepts requests on."""
        url = self.state.get("device_url", "")
        if self.override or not url:
            return
        if self.auth_ok(url):
            return
        host = urlparse(url).hostname
        for port in self.PORTS:
            cand = "http://{}:{}".format(host, port)
            if cand != url and self.auth_ok(cand):
                self.logger("cloud said {} but the Tablo accepts requests at {}".format(url, cand))
                self.state["device_url"] = cand
                return

    def ensure_login(self):
        if not self.logged_in:
            self.login()

    def _cloud_get(self, path, retry=True):
        self.ensure_login()
        h = {
            "User-Agent": CLOUD_UA,
            "Accept": "*/*",
            "Authorization": self.state["auth"],
            "Lighthouse": self.state["lighthouse"],
        }
        url = CLOUD + path.replace("{lh}", self.state["lighthouse"])
        t0 = time.time()
        try:
            r = self.s.get(url, headers=h, timeout=self.timeout)
        except requests.RequestException as e:
            self.logger("cloud GET {} failed after {:.1f}s: {}".format(path, time.time() - t0, e))
            raise TabloError("Can't reach Tablo's cloud service: {}".format(e))
        self.logger("cloud GET {} -> {} ({:.1f}s)".format(path, r.status_code, time.time() - t0))
        if r.status_code in (401, 403) and retry:
            self.login()
            return self._cloud_get(path, retry=False)
        r.raise_for_status()
        return r.json()

    def channels(self, include_fast=False):
        """Channel lineup from the cloud guide, OTA first then FAST."""
        raw = self._cloud_get("/api/v2/account/{lh}/guide/channels/")
        out = []
        for ch in raw:
            kind = ch.get("kind", "ota")
            if kind == "ott" and not include_fast:
                continue
            info = ch.get(kind) or ch.get("ota") or ch.get("ott") or {}
            logo = pick_logo(ch.get("logos") or [])
            major = info.get("major") or 0
            minor = info.get("minor") or 0
            call = info.get("callSign") or ch.get("name") or ch["identifier"]
            out.append({
                "id": ch["identifier"],
                "kind": kind,
                "major": major,
                "minor": minor,
                "number": "{}.{}".format(major, minor) if major else "",
                "call_sign": call,
                "network": info.get("network") or "",
                "name": ch.get("name") or call,
                "logo": logo,
            })
        out.sort(key=lambda c: (0, c["major"], c["minor"], "") if c["major"]
                 else (1, 0, 0, c["call_sign"].lower()))
        return out

    def airings(self, channel_id, day):
        """Guide airings for one channel on one day (YYYY-MM-DD)."""
        return self._cloud_get("/api/v2/account/guide/channels/{}/airings/{}/".format(
            channel_id, day))

    # ------------------------------------------------------------------ local
    def local(self, method, path, body=None, params=None, retry=True):
        """Signed request to the Tablo on the LAN. Returns parsed JSON or None."""
        self.ensure_login()
        if body is not None and not isinstance(body, str):
            body = json.dumps(body)
        body = body or ""
        date = formatdate(usegmt=True)
        h = {
            "Authorization": sign(method, path, body, date),
            "Date": date,
            "Accept": "*/*",
            "User-Agent": LOCAL_UA,
            "Connection": "keep-alive",
        }
        if body:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        t0 = time.time()
        try:
            r = self.s.request(method, self.device_url + path, data=body.encode("utf-8") or None,
                               params=params, headers=h, timeout=self.timeout)
        except requests.RequestException as e:
            self.logger("local {} {} failed after {:.1f}s: {}".format(
                method, self.device_url + path, time.time() - t0, e))
            old = self.device_url
            if retry and not self.override:
                # The Tablo's LAN address may have changed; the cloud knows the new one.
                self.login()
                if self.device_url != old:
                    return self.local(method, path, body, params, retry=False)
            raise TabloError("Can't reach the Tablo at {}. Set its IP address in the add-on "
                             "settings if this address is wrong.".format(self.device_url))
        self.logger("local {} {} -> {} ({:.1f}s)".format(
            method, path, r.status_code, time.time() - t0))
        if r.status_code in (401, 403) and retry:
            # Device only trusts clients after a recent cloud login.
            self.login()
            return self.local(method, path, body, params, retry=False)
        if r.status_code == 204 or not r.content:
            if not r.ok:
                raise TabloError("Tablo returned HTTP {}".format(r.status_code))
            return None
        try:
            j = r.json()
        except ValueError:
            j = None
        if not r.ok:
            msg = r.status_code
            if isinstance(j, dict) and isinstance(j.get("error"), dict):
                msg = j["error"].get("description") or j["error"].get("code") or msg
            raise TabloError("Tablo error: {}".format(msg))
        return j

    def batch(self, paths, chunk=50):
        out = {}
        paths = list(paths)
        for i in range(0, len(paths), chunk):
            res = self.local("POST", "/batch", body=paths[i:i + chunk]) or {}
            out.update(res)
        return out

    # live / playback
    def watch_channel(self, channel_id):
        j = self.local("POST", "/guide/channels/{}/watch".format(channel_id),
                       body=_watch_body(self.state["client_id"]), params="lh")
        if not j or not j.get("playlist_url"):
            raise TabloError("No stream returned (all tuners busy?)")
        return j

    def watch_recording(self, path):
        j = self.local("POST", path.rstrip("/") + "/watch",
                       body=_watch_body(self.state["client_id"]))
        if not j or not j.get("playlist_url"):
            raise TabloError("No stream returned for recording")
        return j

    # server
    def server_info(self):
        return self.local("GET", "/server/info")

    def tuners(self):
        return self.local("GET", "/server/tuners") or []

    def harddrives(self):
        return self.local("GET", "/server/harddrives") or []

    # recordings
    def recording_paths(self):
        return self.local("GET", "/recordings/airings") or []

    def recordings(self):
        """All recordings as full records (via /batch)."""
        paths = self.recording_paths()
        recs = self.batch(paths)
        return [r for r in recs.values() if r]

    def update_recording(self, path, **fields):
        return self.local("PATCH", path, body=fields)

    def delete_recording(self, path):
        return self.local("DELETE", path)

    # guide / scheduling (local)
    def guide_series(self, qualifier=None):
        params = {"qualifier": qualifier} if qualifier else None
        return self.local("GET", "/guide/series", params=params) or []

    def scheduled_airings(self):
        return self.local("GET", "/guide/airings", params={"state": "scheduled"}) or []

    def set_series_schedule(self, series_path, rule):
        """rule: 'all' | 'new' | 'none'"""
        return self.local("PATCH", series_path, body={"schedule": rule})

    def set_airing_scheduled(self, airing_path, scheduled=True):
        return self.local("PATCH", airing_path, body={"scheduled": bool(scheduled)})
