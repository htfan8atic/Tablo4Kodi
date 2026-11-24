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


_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def _wanted_date():
    """Possible (month, day) pairs for the highlighted programme, from Kodi's date string.

    Kodi gives guide dates in its *long* regional format ('Tuesday, November 24, 2026'), but
    short ('11/24/2026', '24/11/2026') and ISO forms are handled too. month is None when the
    month is a word we don't recognise (another language); the day alone is then enough,
    because the Tablo's guide only covers about two weeks."""
    raw = _info("StartDate")
    month = None
    for word in re.findall(r"[^\W\d_]+", raw.lower()):
        if word[:3] in _MONTHS and len(word) >= 3:
            month = _MONTHS.index(word[:3]) + 1
            break
    nums = [int(n) for n in re.findall(r"\d+", raw) if len(n) < 4 and 0 < int(n) <= 31]
    if not nums:
        return None
    if month:
        return set((month, d) for d in nums)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return {(a, b), (b, a)}
    return {(None, nums[0])}


def _date_ok(local, pairs):
    if not pairs:
        return True
    return any(m in (None, local.month) and d == local.day for m, d in pairs)


def _tablo_channel():
    """The Tablo's 'major.minor' channel number for the highlighted programme.
    Kodi may renumber channels (2, 3, 10 ...), so take it from the channel name the add-on
    gave it ('11.1 WXIADT1'); fall back to Kodi's number only if that looks like major.minor."""
    for label in ("ChannelName", "ChannelNumberLabel", "ChannelNumber"):
        m = re.match(r"\s*(\d+)[.\-](\d+)\b", _info(label))
        if m:
            return "{}.{}".format(int(m.group(1)), int(m.group(2)))
    return None


def _airing_channel(r):
    ch = ((r.get("airing_details") or {}).get("channel") or {}).get("channel") or {}
    if ch.get("major") is None:
        return None
    return "{}.{}".format(ch.get("major"), ch.get("minor"))


_SKEW = None


def _kodi_skew():
    """Minutes between the clock Kodi shows and Python's local clock. On some systems (e.g.
    LibreELEC) Kodi's time zone setting and the OS time zone can differ; the guide uses Kodi's."""
    global _SKEW
    if _SKEW is None:
        _SKEW = 0
        m = re.search(r"(\d{1,2}):(\d{2})", xbmc.getInfoLabel("System.Time(hh:mm xx)") or "")
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            low = xbmc.getInfoLabel("System.Time(hh:mm xx)").lower()
            if "pm" in low and h < 12:
                h += 12
            elif "am" in low and h == 12:
                h = 0
            now = datetime.datetime.now()
            diff = (h * 60 + mi) - (now.hour * 60 + now.minute)
            diff = (diff + 720) % 1440 - 720          # -720..719
            _SKEW = int(round(diff / 15.0)) * 15     # time zones move in 15-minute steps
            if _SKEW:
                log("Kodi's clock differs from the system clock by {} minutes; adjusting".format(_SKEW))
    return _SKEW


def _airing_matches(r, chno, hm, date_nums):
    ad = r.get("airing_details") or {}
    if chno and _airing_channel(r) not in (None, chno):
        return False
    dt = guide.parse_time(ad.get("datetime"))
    if not dt:
        return False
    local = dt.astimezone() + datetime.timedelta(minutes=_kodi_skew())
    if hm:
        # allow a couple of minutes' difference between the guide and the Tablo's schedule
        diff = abs((local.hour * 60 + local.minute) - (hm[0] * 60 + hm[1]))
        if min(diff, 1440 - diff) > 2:
            return False
    if not _date_ok(local, date_nums):
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
    seen = []
    title_match = None
    for s in _all_series(tablo):
        if _norm((s.get("series") or {}).get("title")) != want:
            continue
        title_match = title_match or s
        eps = tablo.local("GET", s["path"].rstrip("/") + "/episodes") or []
        airings = [r for r in tablo.batch(eps).values() if r]
        for r in airings:
            if _airing_matches(r, chno, hm, date_nums):
                return "series", s, r
        # channel numbering can differ (e.g. a renumbered or virtual channel): if exactly one
        # airing of this show matches the date and time, that's the one
        same_time = [r for r in airings if _airing_matches(r, None, hm, date_nums)]
        if len(same_time) == 1:
            return "series", s, same_time[0]
        seen += ["{} ch {}".format((r.get("airing_details") or {}).get("datetime"), _airing_channel(r))
                 for r in airings]
    if seen or title_match:
        log("record from guide: show found but no airing matched; Tablo has: {}".format(
            ", ".join(sorted(seen)[:20]) or "no upcoming airings"))
    else:
        log("record from guide: no show titled {!r} in the Tablo's guide".format(title))
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
    if title_match:
        return "series", title_match, None
    return None, None, None


def run():
    title = _info("Title")
    if not title:
        return notify("Highlight a programme in the TV guide first", error=True)
    chno = _tablo_channel()
    hm = _wanted_time()
    date_nums = _wanted_date()
    log("record from guide: {!r} ch {} (Kodi: {!r} / {!r}) at {!r} {!r}".format(
        title, chno, _info("ChannelName"), _info("ChannelNumberLabel"),
        _info("StartDate"), _info("StartTime")))
    tablo = get_tablo()
    try:
        kind, parent, airing = _find(tablo, title, chno, hm, date_nums)
        if not airing and kind == "series":
            pass  # offer the series options below
        elif not airing:
            return xbmcgui.Dialog().ok(
                "Record with Tablo",
                "Couldn't find \"{}\" at that time on the Tablo.\n"
                "Use Record a show in the Tablo add-on instead.".format(title))
        # Order: this episode, new episodes, all episodes, then the cancel options.
        options, actions = [], []
        scheduled = False
        if airing:
            scheduled = (airing.get("schedule") or {}).get("state") in ("scheduled", "conflicted")
            ep = airing.get("episode") or {}
            heading = title + (" - " + ep["title"] if ep.get("title") else "")
            when = guide.parse_time((airing.get("airing_details") or {}).get("datetime"))
            if when:
                when = when.astimezone() + datetime.timedelta(minutes=_kodi_skew())
                heading += "  ({} {}, {}:{:02d} {})".format(
                    when.strftime("%a"), when.strftime("%b"), when.day,
                    (when.hour % 12) or 12, when.minute, "PM" if when.hour >= 12 else "AM")
            if not scheduled:
                options.append("Record this episode only" if kind == "series" else "Record this airing")
                actions.append(("airing", True))
        else:
            heading = "{} (couldn't match this exact airing on the Tablo)".format(title)
        rule = (parent.get("schedule_rule") or "none") if kind == "series" else None
        if kind == "series":
            if rule != "new":
                options.append("Record new episodes only")
                actions.append(("rule", "new"))
            if rule != "all":
                options.append("Record all episodes")
                actions.append(("rule", "all"))
        if scheduled:
            options.append("Don't record this episode" if kind == "series" else "Don't record this airing")
            actions.append(("airing", False))
        if kind == "series" and rule != "none":
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
