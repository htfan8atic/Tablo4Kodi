# -*- coding: utf-8 -*-
"""'Record with Tablo' in the context menu of Kodi's TV guide.

IPTV Simple can't record, so Kodi's own Record button does nothing for Tablo channels.
This finds the highlighted programme on the Tablo (same show, channel, date and time) and
offers to record that airing or the whole series.
"""

import datetime
import json
import os
import re
import time

import xbmc
import xbmcgui

from . import guide
from .kodiutils import get_tablo, log, notify, profile_dir
from .tablo import AuthError, TabloError

MOVIE_CACHE = "movie_cache.json"
CACHE_TTL = 6 * 3600


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _info(label):
    return xbmc.getInfoLabel("ListItem." + label)


def _wanted_time():
    """(hour, minute) of the highlighted programme, from Kodi's regional time string."""
    raw = _info("StartTime")
    m = re.search(r"(\d{1,2})[:.](\d{2})", raw)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    low = raw.lower()
    if "pm" in low and h < 12:
        h += 12
    elif "am" in low and h == 12:
        h = 0
    return h, mi


def _wanted_date_numbers():
    """Numbers in Kodi's regional date string (e.g. '11/17/2026' -> {11, 17, 2026})."""
    return set(int(n) for n in re.findall(r"\d+", _info("StartDate")))


def _airing_matches(r, chno, hm, date_nums):
    ad = r.get("airing_details") or {}
    ch = (ad.get("channel") or {}).get("channel") or {}
    if chno and "{}.{}".format(ch.get("major"), ch.get("minor")) != chno:
        return False
    dt = guide.parse_time(ad.get("datetime"))
    if not dt:
        return False
    local = dt.astimezone()
    if hm and (local.hour, local.minute) != hm:
        return False
    if date_nums and not {local.day, local.month} <= date_nums:
        return False
    return True


def _cached(tablo, name, list_path, label):
    p = os.path.join(profile_dir(), name)
    try:
        with open(p) as f:
            c = json.load(f)
        if time.time() - c["t"] < CACHE_TTL:
            return c["items"]
    except (IOError, OSError, ValueError, KeyError):
        pass
    dlg = xbmcgui.DialogProgressBG()
    dlg.create("Tablo", "Loading {}...".format(label))
    try:
        paths = tablo.local("GET", list_path) or []
        items = [r for r in tablo.batch(paths).values() if r]
    finally:
        dlg.close()
    with open(p, "w") as f:
        json.dump({"t": time.time(), "items": items}, f)
    return items


def _find(tablo, title, chno, hm, date_nums):
    """Return (kind, parent record, airing record) or (None, None, None)."""
    from .plugin import _all_series  # shared cache with 'Record a show'
    want = _norm(title)
    for s in _all_series(tablo):
        if _norm((s.get("series") or {}).get("title")) != want:
            continue
        eps = tablo.local("GET", s["path"].rstrip("/") + "/episodes") or []
        for r in tablo.batch(eps).values():
            if r and _airing_matches(r, chno, hm, date_nums):
                return "series", s, r
    try:
        movies = _cached(tablo, MOVIE_CACHE, "/guide/movies", "guide movies")
    except TabloError as e:  # not every Tablo exposes a movie list; series still worked above
        log("movie lookup unavailable: {}".format(e))
        movies = []
    for m in movies:
        if _norm((m.get("movie") or {}).get("title")) != want:
            continue
        airings = tablo.local("GET", m["path"].rstrip("/") + "/airings") or []
        for r in tablo.batch(airings).values():
            if r and _airing_matches(r, chno, hm, date_nums):
                return "movie", m, r
    return None, None, None


def run():
    title = _info("Title")
    if not title:
        return notify("Highlight a programme in the TV guide first", error=True)
    chno = _info("ChannelNumberLabel").strip()
    hm = _wanted_time()
    date_nums = _wanted_date_numbers()
    log("record from guide: {!r} ch {} at {} {}".format(title, chno, _info("StartDate"), _info("StartTime")))
    tablo = get_tablo()
    try:
        kind, parent, airing = _find(tablo, title, chno, hm, date_nums)
        if not airing:
            return xbmcgui.Dialog().ok(
                "Record with Tablo",
                "Couldn't find \"{}\" at that time on the Tablo.\n"
                "Use Record a show in the Tablo add-on instead.".format(title))
        scheduled = (airing.get("schedule") or {}).get("state") in ("scheduled", "conflicted")
        ep = airing.get("episode") or {}
        heading = title + (" - " + ep["title"] if ep.get("title") else "")
        options, actions = [], []
        if scheduled:
            options.append("Don't record this airing")
            actions.append(("airing", False))
        else:
            options.append("Record this airing")
            actions.append(("airing", True))
        if kind == "series":
            rule = parent.get("schedule_rule") or "none"
            if rule != "all":
                options.append("Record all episodes")
                actions.append(("rule", "all"))
            if rule != "new":
                options.append("Record new episodes only")
                actions.append(("rule", "new"))
            if rule != "none":
                options.append("Stop recording this series")
                actions.append(("rule", "none"))
        choice = xbmcgui.Dialog().select(heading, options)
        if choice < 0:
            return
        what, value = actions[choice]
        if what == "airing":
            tablo.set_airing_scheduled(airing["path"], value)
            notify("Recording scheduled" if value else "Recording cancelled")
        else:
            tablo.set_series_schedule(parent["path"], value)
            try:
                os.remove(os.path.join(profile_dir(), "series_cache.json"))
            except OSError:
                pass
            notify({"all": "Recording all episodes", "new": "Recording new episodes",
                    "none": "Series recording stopped"}[value])
    except AuthError as e:
        notify(str(e), error=True)
    except (TabloError, Exception) as e:  # noqa: B014
        log("record from guide failed: {}".format(e), xbmc.LOGERROR)
        notify("Couldn't schedule: {}".format(e), error=True)
