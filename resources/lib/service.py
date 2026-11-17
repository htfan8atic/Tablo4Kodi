# -*- coding: utf-8 -*-
"""Background service.

* Serves /playlist.m3u, /epg.xml and /live/<channel>.m3u8 on 127.0.0.1 for
  IPTV Simple Client.
* Refreshes the guide from the Tablo cloud on a timer.
* Saves resume position / watched state for recordings played from the plugin.
"""

import datetime
import os
import re
import threading
import time

try:
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
except ImportError:  # pragma: no cover
    from http.server import HTTPServer as ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urljoin

import xbmc
import xbmcgui

from . import guide, logocache
from .kodiutils import (base_url, get_tablo, log, logo_style, profile_dir, server_port,
                        setting_bool, setting_int)
from .tablo import TabloError

M3U = "playlist.m3u"
EPG = "epg.xml"
PLAYING_PROP = "tablo4g.recording"
HOME = xbmcgui.Window(10000)

_URI_ATTR = re.compile(r'URI="([^"]+)"')


def absolutize_playlist(text, url):
    """Make every URI in an HLS playlist absolute so it works when served from localhost."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(line)
        elif s.startswith("#"):
            out.append(_URI_ATTR.sub(lambda m: 'URI="{}"'.format(urljoin(url, m.group(1))), line))
        else:
            out.append(urljoin(url, s))
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    tablo = None

    def log_message(self, fmt, *args):
        log("http: " + (fmt % args), xbmc.LOGDEBUG)

    def _send(self, code, body=b"", ctype="text/plain"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _file(self, name, ctype):
        p = os.path.join(profile_dir(), name)
        if not os.path.exists(p):
            return self._send(503, "Guide not built yet")
        with open(p, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_HEAD(self):
        # Kodi probes stream URLs with HEAD on its GUI thread. Answer instantly;
        # tuning happens on the GET, which runs on the player thread.
        path = self.path.split("?", 1)[0]
        if re.match(r"^/live/", path):
            ctype = "application/vnd.apple.mpegurl"
        elif re.match(r"^/logo/", path):
            ctype = "image/png"
        elif path == "/" + M3U:
            ctype = "audio/x-mpegurl"
        elif path == "/" + EPG:
            ctype = "application/xml"
        else:
            return self._send(404, "Not found")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/" + M3U:
            return self._file(M3U, "audio/x-mpegurl")
        if path == "/" + EPG:
            return self._file(EPG, "application/xml")
        m = re.match(r"^/logo/([0-9a-f]+)\.png$", path)
        if m:
            p = logocache.path_for(profile_dir(), m.group(1))
            if p and os.path.exists(p):
                with open(p, "rb") as f:
                    data = f.read()
                ctype = ("image/png" if data[:4] == b"\x89PNG" else
                         "image/svg+xml" if data.lstrip()[:1] == b"<" else "image/jpeg")
                return self._send(200, data, ctype)
            return self._send(404, "No such logo")
        m = re.match(r"^/live/([^/]+?)(?:\.m3u8)?$", path)
        if m:
            return self._live(m.group(1))
        self._send(404, "Not found")

    def _live(self, channel_id):
        try:
            j = self.tablo.watch_channel(channel_id)
            r = self.tablo.s.get(j["playlist_url"], timeout=15)
            r.raise_for_status()
            body = absolutize_playlist(r.text, r.url)
            log("tuned {} -> {}".format(channel_id, j["playlist_url"]))
            self._send(200, body, "application/vnd.apple.mpegurl")
        except (TabloError, Exception) as e:  # noqa: B014
            log("live {} failed: {}".format(channel_id, e), xbmc.LOGERROR)
            self._send(503, str(e))


class Server(object):
    def __init__(self, tablo):
        Handler.tablo = tablo
        self.httpd = ThreadingHTTPServer(("127.0.0.1", server_port()), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True

    def start(self):
        self.thread.start()
        log("serving on {}".format(base_url()))

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def reload_iptv_simple():
    """IPTV Simple reads the channel list once at startup. When channels or logos change,
    restart it so Kodi shows them now instead of after the next Kodi restart."""
    if not xbmc.getCondVisibility("System.AddonIsEnabled(pvr.iptvsimple)"):
        return
    log("channel list changed; reloading IPTV Simple")
    for enabled in ("false", "true"):
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled",'
                            '"params":{"addonid":"pvr.iptvsimple","enabled":%s}}' % enabled)
        xbmc.sleep(1500)


REFRESH_REQUEST = "tablo4g.refresh_request"   # set by the plugin: a token
REFRESH_DONE = "tablo4g.refresh_done"         # set by the service: "<token>|<channels or error>"
SERVICE_ALIVE = "tablo4g.service_alive"       # heartbeat, so the plugin knows the service is there
LOCK = "refresh.lock"
LOCK_STALE = 15 * 60


class RefreshBusy(Exception):
    pass


def _lock(wait=120):
    """Only one guide refresh at a time, across the service and plugin."""
    path = os.path.join(profile_dir(), LOCK)
    deadline = time.time() + wait
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(time.time()).encode())
            os.close(fd)
            return path
        except OSError:
            try:
                if time.time() - os.path.getmtime(path) > LOCK_STALE:  # left by a crash
                    os.remove(path)
                    continue
            except OSError:
                continue
            if time.time() >= deadline:
                raise RefreshBusy("another guide refresh is still running")
            xbmc.sleep(500)


def refresh_guide(tablo, wait=120):
    path = _lock(wait)
    try:
        return _refresh_guide(tablo)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _refresh_guide(tablo):
    """Fetch channels + airings and write M3U / XMLTV into the profile folder."""
    include_fast = setting_bool("include_fast")
    days = max(1, min(14, setting_int("guide_days", 3)))
    channels = tablo.channels(include_fast=include_fast)
    from .tablo import LOGO_KINDS_SEEN
    log("logo versions offered by Tablo: {}".format(", ".join(sorted(LOGO_KINDS_SEEN)) or "none"))
    style = logo_style()
    made = logocache.build(channels, tablo.s, profile_dir(), style, log)
    if made:
        log("prepared {} channel logos".format(made))
    logocache.apply(channels, profile_dir(), style, base_url())
    today = datetime.date.today()
    airings = {}
    for c in channels:
        lst = []
        for d in range(days):
            day = (today + datetime.timedelta(days=d)).isoformat()
            try:
                lst.extend(tablo.airings(c["id"], day) or [])
            except Exception as e:  # one bad channel shouldn't kill the guide
                log("airings {} {} failed: {}".format(c["id"], day, e), xbmc.LOGWARNING)
        airings[c["id"]] = lst
    pd = profile_dir()
    m3u = guide.build_m3u(channels, base_url())
    try:
        with open(os.path.join(pd, M3U), encoding="utf-8") as f:
            m3u_changed = f.read() != m3u
    except (IOError, OSError):
        m3u_changed = False  # first run: IPTV Simple hasn't been set up against it yet
    for name, data in ((M3U, m3u), (EPG, guide.build_xmltv(channels, airings))):
        tmp = os.path.join(pd, "{}.{}.{}.tmp".format(name, os.getpid(), threading.get_ident()))
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, os.path.join(pd, name))
    log("guide refreshed: {} channels, {} days".format(len(channels), days))
    if m3u_changed:
        reload_iptv_simple()
    return len(channels)


class Player(xbmc.Player):
    """Tracks recordings started from the plugin and reports position back."""

    def __init__(self, tablo):
        xbmc.Player.__init__(self)
        self.tablo = tablo
        self.path = None
        self.pos = 0.0
        self.total = 0.0

    def onAVStarted(self):
        self.path = HOME.getProperty(PLAYING_PROP) or None
        HOME.clearProperty(PLAYING_PROP)

    def tick(self):
        if self.path and self.isPlayingVideo():
            try:
                self.pos = self.getTime()
                self.total = self.getTotalTime() or self.total
            except RuntimeError:
                pass

    def _report(self, ended):
        path, self.path = self.path, None
        if not path:
            return
        try:
            if ended or (self.total and self.pos >= self.total * 0.92):
                self.tablo.update_recording(path, watched=True, position=0)
            elif self.pos > 30:
                self.tablo.update_recording(path, position=int(self.pos))
        except Exception as e:
            log("saving position failed: {}".format(e), xbmc.LOGWARNING)
        self.pos = self.total = 0.0

    def onPlayBackStopped(self):
        self._report(False)

    def onPlayBackEnded(self):
        self._report(True)


class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.changed = False

    def onSettingsChanged(self):
        self.changed = True


def run():
    monitor = Monitor()
    log("service starting")
    tablo = get_tablo()
    server = Server(tablo)
    server.start()
    player = Player(tablo)
    next_refresh = 0
    try:
        while not monitor.abortRequested():
            if monitor.changed:
                monitor.changed = False
                tablo = get_tablo()
                Handler.tablo = tablo
                player.tablo = tablo
                next_refresh = 0
            HOME.setProperty(SERVICE_ALIVE, str(int(time.time())))
            request = HOME.getProperty(REFRESH_REQUEST)
            if request:
                HOME.clearProperty(REFRESH_REQUEST)
                next_refresh = 0
            if time.time() >= next_refresh:
                if tablo.email and tablo.password:
                    try:
                        log("refreshing guide...")
                        n = refresh_guide(tablo)
                        next_refresh = time.time() + 3600 * max(1, setting_int("refresh_hours", 6))
                        result = str(n)
                    except Exception as e:
                        log("guide refresh failed: {}".format(e), xbmc.LOGERROR)
                        next_refresh = time.time() + 600
                        result = "error: {}".format(e)
                else:
                    next_refresh = time.time() + 60
                    result = "error: enter your Tablo email and password in settings"
                if request:
                    HOME.setProperty(REFRESH_DONE, "{}|{}".format(request, result))
            player.tick()
            if monitor.waitForAbort(1):
                break
    finally:
        server.stop()
