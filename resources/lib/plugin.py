# -*- coding: utf-8 -*-
"""Video add-on UI: recordings, scheduling, status, IPTV Simple setup."""

import datetime
import json
import os
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import guide, logocache
from .kodiutils import addon, base_url, get_tablo, log, logo_style, notify, profile_dir
from .service import (PLAYING_PROP, REFRESH_DONE, REFRESH_REQUEST, SERVICE_ALIVE,
                      refresh_guide)
from .tablo import AuthError, TabloError

HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else -1
BASE = sys.argv[0] if sys.argv else "plugin://plugin.video.tablo4g/"
HOME = xbmcgui.Window(10000)
SERIES_CACHE = "series_cache.json"
SERIES_TTL = 6 * 3600


def url(**kw):
    return BASE + "?" + urlencode(kw)


def add_dir(label, action, art=None, info=None, ctx=None, folder=True, playable=False, **kw):
    li = xbmcgui.ListItem(label)
    if art:
        li.setArt(art)
    if info:
        li.setInfo("video", info)
    if ctx:
        li.addContextMenuItems(ctx)
    if playable:
        li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, url(action=action, **kw), li, isFolder=folder)


def end(content=None, cache=False):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache)


def local_time(iso):
    dt = guide.parse_time(iso)
    return dt.astimezone() if dt else None


def fmt_when(iso):
    dt = local_time(iso)
    return dt.strftime("%a %b %d %I:%M %p").replace(" 0", " ") if dt else ""


def image_url(tablo, image_id):
    if not image_id:
        return ""
    host = urlparse(tablo.device_url).hostname
    return "http://{}/images/{}".format(host, image_id)


# ---------------------------------------------------------------- root
def root():
    add_dir("Test connection", "diag", folder=False)
    add_dir("Live TV", "channels")
    add_dir("Recordings", "recordings")
    add_dir("Upcoming recordings", "upcoming")
    add_dir("Record a show", "shows_menu")
    add_dir("Series recording rules", "rules")
    add_dir("Tablo status", "status", folder=False)
    add_dir("Refresh TV guide now", "refresh", folder=False)
    add_dir("Set up IPTV Simple Client", "setup_iptv", folder=False)
    add_dir("Settings", "settings", folder=False)
    end()


# ---------------------------------------------------------------- live
def channels(tablo):
    from .kodiutils import setting_bool
    chans = logocache.apply(tablo.channels(include_fast=setting_bool("include_fast")),
                            profile_dir(), logo_style(), base_url())
    for c in chans:
        label = "{} {}".format(c["number"], c["call_sign"]).strip()
        if c["network"]:
            label += "  [COLOR grey]{}[/COLOR]".format(c["network"])
        add_dir(label, "play_live", art={"icon": c["logo"], "thumb": c["logo"]},
                info={"title": label, "mediatype": "video"},
                folder=False, playable=True, id=c["id"])
    end("videos")


def play_live(tablo, cid):
    li = xbmcgui.ListItem(path="{}/live/{}.m3u8".format(base_url(), cid))
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


# ---------------------------------------------------------------- recordings
def _rec_show_key(r):
    for k in ("series_path", "movie_path", "sport_path", "channel_path"):
        if r.get(k):
            return r[k]
    return r.get("path", "")


def _rec_show_title(r):
    ad = r.get("airing_details") or {}
    return (ad.get("show_title") or (r.get("movie_airing") or {}).get("title")
            or (r.get("event") or {}).get("title") or "Other")


def _rec_title(r):
    ep = r.get("episode") or {}
    ev = r.get("event") or {}
    return ep.get("title") or ev.get("title") or _rec_show_title(r)


def _rec_when(r):
    return (r.get("airing_details") or {}).get("datetime", "")


def recordings(tablo):
    recs = tablo.recordings()
    shows = {}
    for r in recs:
        k = _rec_show_key(r)
        s = shows.setdefault(k, {"title": _rec_show_title(r), "count": 0, "unwatched": 0,
                                 "latest": "", "thumb": ""})
        s["count"] += 1
        if not (r.get("user_info") or {}).get("watched"):
            s["unwatched"] += 1
        when = _rec_when(r)
        if when >= s["latest"]:
            s["latest"] = when
            s["thumb"] = image_url(tablo, (r.get("snapshot_image") or {}).get("image_id"))
    for k, s in sorted(shows.items(), key=lambda kv: kv[1]["latest"], reverse=True):
        label = s["title"]
        if s["unwatched"]:
            label += "  [COLOR yellow]({} new)[/COLOR]".format(s["unwatched"])
        ctx = [("Delete all watched episodes",
                "RunPlugin({})".format(url(action="delete_watched", show=k)))]
        add_dir(label, "episodes", art={"thumb": s["thumb"]}, ctx=ctx, show=k)
    if not shows:
        add_dir("[No recordings]", "noop", folder=False)
    end("tvshows")


def episodes(tablo, show_key):
    recs = [r for r in tablo.recordings() if _rec_show_key(r) == show_key]
    recs.sort(key=_rec_when, reverse=True)
    for r in recs:
        ui = r.get("user_info") or {}
        vd = r.get("video_details") or {}
        ep = r.get("episode") or {}
        state = vd.get("state", "")
        label = _rec_title(r)
        tags = []
        if state == "recording":
            tags.append("[COLOR red]REC[/COLOR]")
        elif state == "failed":
            tags.append("[COLOR red]FAILED[/COLOR]")
        if ui.get("protected"):
            tags.append("[COLOR orange]protected[/COLOR]")
        if tags:
            label += "  " + " ".join(tags)
        label2 = fmt_when(_rec_when(r))
        info = {
            "title": "{}  [COLOR grey]{}[/COLOR]".format(label, label2),
            "tvshowtitle": _rec_show_title(r),
            "plot": ep.get("description") or (r.get("airing_details") or {}).get("description") or "",
            "duration": int(vd.get("duration") or 0),
            "playcount": 1 if ui.get("watched") else 0,
            "mediatype": "episode",
            "aired": (ep.get("orig_air_date") or "")[:10],
        }
        if ep.get("season_number"):
            info["season"] = ep["season_number"]
        if ep.get("number"):
            info["episode"] = ep["number"]
        p = r["path"]
        ctx = [
            ("Mark unwatched" if ui.get("watched") else "Mark watched",
             "RunPlugin({})".format(url(action="mark", path=p,
                                        watched="0" if ui.get("watched") else "1"))),
            ("Unprotect" if ui.get("protected") else "Protect",
             "RunPlugin({})".format(url(action="protect", path=p,
                                        on="0" if ui.get("protected") else "1"))),
        ]
        if not ui.get("protected"):
            ctx.append(("Delete recording", "RunPlugin({})".format(url(action="delete", path=p))))
        add_dir(info["title"], "play_rec",
                art={"thumb": image_url(tablo, (r.get("snapshot_image") or {}).get("image_id"))},
                info=info, ctx=ctx, folder=False, playable=True, path=p,
                pos=str(ui.get("position") or 0))
    end("episodes")


def play_rec(tablo, path, pos):
    pos = int(float(pos or 0))
    start = 0
    if pos > 30:
        m, s = divmod(pos, 60)
        h, m = divmod(m, 60)
        choice = xbmcgui.Dialog().contextmenu(
            ["Resume from {}:{:02d}:{:02d}".format(h, m, s), "Play from beginning"])
        if choice < 0:
            return xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        start = pos if choice == 0 else 0
    try:
        j = tablo.watch_recording(path)
    except TabloError as e:
        notify(str(e), error=True)
        return xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    li = xbmcgui.ListItem(path=j["playlist_url"])
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setContentLookup(False)
    if xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)"):
        li.setProperty("inputstream", "inputstream.adaptive")
        li.setProperty("inputstream.adaptive.manifest_type", "hls")
    if start:
        li.setProperty("StartOffset", str(start))
    HOME.setProperty(PLAYING_PROP, path)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def mark(tablo, path, watched):
    tablo.update_recording(path, watched=watched == "1")
    xbmc.executebuiltin("Container.Refresh")


def protect(tablo, path, on):
    tablo.update_recording(path, protected=on == "1")
    xbmc.executebuiltin("Container.Refresh")


def delete(tablo, path):
    if xbmcgui.Dialog().yesno("Tablo", "Delete this recording?"):
        tablo.delete_recording(path)
        notify("Recording deleted")
        xbmc.executebuiltin("Container.Refresh")


def delete_watched(tablo, show_key):
    recs = [r for r in tablo.recordings() if _rec_show_key(r) == show_key
            and (r.get("user_info") or {}).get("watched")
            and not (r.get("user_info") or {}).get("protected")]
    if not recs:
        return notify("No watched, unprotected episodes")
    if xbmcgui.Dialog().yesno("Tablo", "Delete {} watched episode(s)?".format(len(recs))):
        for r in recs:
            tablo.delete_recording(r["path"])
        notify("Deleted {} recording(s)".format(len(recs)))
        xbmc.executebuiltin("Container.Refresh")


# ---------------------------------------------------------------- scheduling
def upcoming(tablo):
    paths = tablo.scheduled_airings()
    recs = [r for r in tablo.batch(paths).values() if r]
    recs.sort(key=lambda r: (r.get("airing_details") or {}).get("datetime", ""))
    for r in recs:
        ad = r.get("airing_details") or {}
        title = ad.get("show_title") or _rec_title(r)
        sub = (r.get("episode") or {}).get("title")
        ch = ((ad.get("channel") or {}).get("channel") or {})
        label = "{}  {}{}  [COLOR grey]{}.{} {}[/COLOR]".format(
            fmt_when(ad.get("datetime")), title, " - " + sub if sub else "",
            ch.get("major", ""), ch.get("minor", ""), ch.get("call_sign", ""))
        conflicted = (r.get("schedule") or {}).get("state") == "conflicted"
        if conflicted:
            label += "  [COLOR red]CONFLICT[/COLOR]"
        ctx = [("Don't record this airing",
                "RunPlugin({})".format(url(action="sched_airing", path=r["path"], on="0")))]
        add_dir(label, "noop", ctx=ctx, folder=False,
                info={"plot": (r.get("episode") or {}).get("description", "")})
    if not recs:
        add_dir("[Nothing scheduled]", "noop", folder=False)
    end()


def _all_series(tablo, force=False):
    """All guide series records, cached because there can be hundreds."""
    p = os.path.join(profile_dir(), SERIES_CACHE)
    if not force:
        try:
            with open(p) as f:
                c = json.load(f)
            if time.time() - c["t"] < SERIES_TTL:
                return c["series"]
        except (IOError, OSError, ValueError, KeyError):
            pass
    dlg = xbmcgui.DialogProgress()
    dlg.create("Tablo", "Loading guide shows...")
    try:
        paths = tablo.guide_series()
        series = []
        for i in range(0, len(paths), 50):
            series.extend(r for r in tablo.batch(paths[i:i + 50]).values() if r)
            dlg.update(int(100.0 * (i + 50) / max(1, len(paths))))
    finally:
        dlg.close()
    with open(p, "w") as f:
        json.dump({"t": time.time(), "series": series}, f)
    return series


def _series_item(tablo, s):
    title = (s.get("series") or {}).get("title", "?")
    rule = s.get("schedule_rule") or (s.get("schedule") or {}).get("rule") or "none"
    label = title
    if rule != "none":
        label += "  [COLOR red]● {}[/COLOR]".format("All" if rule == "all" else "New")
    ser = s.get("series") or {}
    thumb = image_url(tablo, (ser.get("thumbnail_image") or {}).get("image_id"))
    add_dir(label, "series", art={"thumb": thumb, "poster": thumb},
            info={"plot": ser.get("description", ""), "title": title},
            path=s["path"], title=title)


def shows_menu():
    add_dir("Search...", "search")
    add_dir("New episodes", "shows", q="new")
    add_dir("Premieres", "shows", q="premiering")
    add_dir("Primetime", "shows", q="primetime")
    add_dir("All shows", "shows", q="")
    end()


def shows(tablo, q):
    if q:
        paths = set(tablo.guide_series(qualifier=q))
        series = [s for s in _all_series(tablo) if s["path"] in paths]
        missing = paths - set(s["path"] for s in series)
        if missing:
            series += [r for r in tablo.batch(missing).values() if r]
    else:
        series = _all_series(tablo)
    for s in sorted(series, key=lambda s: ((s.get("series") or {}).get("title") or "").lower()):
        _series_item(tablo, s)
    end("tvshows")


def search(tablo):
    term = xbmcgui.Dialog().input("Search shows")
    if not term:
        return end()
    term = term.lower()
    hits = [s for s in _all_series(tablo)
            if term in ((s.get("series") or {}).get("title") or "").lower()]
    for s in sorted(hits, key=lambda s: (s.get("series") or {}).get("title", "")):
        _series_item(tablo, s)
    if not hits:
        add_dir("[No matches]", "noop", folder=False)
    end("tvshows")


def rules(tablo):
    series = [s for s in _all_series(tablo, force=True)
              if (s.get("schedule_rule") or "none") != "none"]
    for s in sorted(series, key=lambda s: (s.get("series") or {}).get("title", "")):
        _series_item(tablo, s)
    if not series:
        add_dir("[No series recordings]", "noop", folder=False)
    end("tvshows")


def series(tablo, path, title):
    """Series page: change the rule, or pick single episodes."""
    add_dir("[B]Record all episodes[/B]", "set_rule", folder=False, path=path, rule="all")
    add_dir("[B]Record new episodes only[/B]", "set_rule", folder=False, path=path, rule="new")
    add_dir("[B]Don't record this series[/B]", "set_rule", folder=False, path=path, rule="none")
    try:
        eps = tablo.local("GET", path.rstrip("/") + "/episodes") or []
        recs = [r for r in tablo.batch(eps).values() if r]
    except TabloError as e:
        log("episodes for {} failed: {}".format(path, e))
        recs = []
    now = datetime.datetime.now(guide.UTC)
    upcoming_eps = []
    for r in recs:
        dt = guide.parse_time((r.get("airing_details") or {}).get("datetime"))
        if dt and dt > now:
            upcoming_eps.append((dt, r))
    for dt, r in sorted(upcoming_eps, key=lambda x: x[0]):
        ep = r.get("episode") or {}
        state = (r.get("schedule") or {}).get("state", "none")
        on = state in ("scheduled", "conflicted")
        label = "{}  {}".format(fmt_when(r["airing_details"]["datetime"]),
                                ep.get("title") or title)
        if on:
            label += "  [COLOR red]● REC[/COLOR]"
        add_dir(label, "sched_airing", folder=False, path=r["path"], on="0" if on else "1",
                info={"plot": ep.get("description", "")})
    end()


def set_rule(tablo, path, rule):
    tablo.set_series_schedule(path, rule)
    try:
        os.remove(os.path.join(profile_dir(), SERIES_CACHE))
    except OSError:
        pass
    notify({"all": "Recording all episodes", "new": "Recording new episodes",
            "none": "Series recording cancelled"}[rule])
    xbmc.executebuiltin("Container.Refresh")


def sched_airing(tablo, path, on):
    tablo.set_airing_scheduled(path, on == "1")
    notify("Recording scheduled" if on == "1" else "Recording cancelled")
    xbmc.executebuiltin("Container.Refresh")


# ---------------------------------------------------------------- misc
def gb(n):
    return "{:.1f} GB".format((n or 0) / 1e9)


def status(tablo):
    info = tablo.server_info() or {}
    lines = ["[B]{}[/B]  ({})".format(info.get("name", tablo.state.get("device_name", "Tablo")),
                                      tablo.device_url),
             "Firmware: {}".format(info.get("version", "?")), ""]
    tuners = tablo.tuners()
    lines.append("[B]Tuners[/B]: {} of {} in use".format(
        sum(1 for t in tuners if t.get("in_use")), len(tuners)))
    for i, t in enumerate(tuners, 1):
        lines.append("  {}: {}".format(i, "recording" if t.get("recording")
                                       else ("in use" if t.get("in_use") else "idle")))
    lines.append("")
    lines.append("[B]Storage[/B]")
    for d in tablo.harddrives():
        lines.append("  {}: {} free of {}".format(d.get("name", "drive"), gb(d.get("free")),
                                                gb(d.get("size"))))
    xbmcgui.Dialog().textviewer("Tablo status", "\n".join(lines))


def _must_answer(tablo, base):
    if not tablo.probe(base):
        raise TabloError("no answer")
    return ""


def diag(tablo):
    """Run each step on its own and show which one fails."""
    import requests
    lines = []
    dlg = xbmcgui.DialogProgress()
    dlg.create("Tablo", "Testing...")

    def step(name, fn):
        t0 = time.time()
        try:
            res = fn()
            lines.append("[COLOR green]OK[/COLOR]   {} ({:.1f}s) {}".format(name, time.time() - t0, res or ""))
            return True
        except Exception as e:
            lines.append("[COLOR red]FAIL[/COLOR] {} ({:.1f}s): {}".format(name, time.time() - t0, e))
            return False

    try:
        dlg.update(10, "Signing in to Tablo cloud...")
        if step("Cloud sign-in", lambda: "device '{}' at {}".format(
                tablo.login()["device_name"], tablo.device_url)):
            dlg.update(35, "Getting channel list...")
            step("Channel list", lambda: "{} channels".format(len(tablo.channels())))
            dlg.update(50, "Looking for the Tablo on your network...")
            host = urlparse(tablo.device_url).hostname
            for port in tablo.PORTS:
                base = "http://{}:{}".format(host, port)
                step("Tablo answers at {}".format(base), lambda b=base: _must_answer(tablo, b))
            dlg.update(70, "Contacting the Tablo on your network...")
            step("Tablo on LAN", lambda: "firmware {}".format((tablo.server_info() or {}).get("version")))
        dlg.update(85, "Checking the add-on's local service...")
        step("Local service", lambda: "playlist HTTP {}".format(
            requests.get(base_url() + "/playlist.m3u", timeout=3).status_code))
    finally:
        dlg.close()
    lines.append("")
    lines.append("If 'Local service' fails, the background service isn't running: restart Kodi.")
    lines.append("If it returns HTTP 503, the guide hasn't been built yet; use 'Refresh TV guide now'.")
    xbmcgui.Dialog().textviewer("Tablo connection test", "\n".join(lines))


def refresh(tablo):
    """Ask the background service to refresh (so two refreshes never overlap); run it here only
    if the service isn't running."""
    try:
        alive = time.time() - int(HOME.getProperty(SERVICE_ALIVE) or 0) < 10
    except ValueError:
        alive = False
    if not alive:
        n = refresh_guide(tablo, force_reload=True)
        return notify("Guide refreshed ({} channels)".format(n))
    token = str(time.time())
    HOME.clearProperty(REFRESH_DONE)
    HOME.setProperty(REFRESH_REQUEST, token)
    dlg = xbmcgui.DialogProgressBG()
    dlg.create("Tablo", "Refreshing TV guide...")
    try:
        deadline = time.time() + 300
        while time.time() < deadline:
            done = HOME.getProperty(REFRESH_DONE)
            if done.startswith(token + "|"):
                result = done.split("|", 1)[1]
                if result.startswith("error"):
                    return notify("Guide refresh failed: " + result[7:], error=True)
                return notify("Guide refreshed ({} channels)".format(result))
            xbmc.sleep(500)
        notify("Guide refresh is taking a while; it will finish in the background")
    finally:
        dlg.close()


def setup_iptv():
    if not xbmc.getCondVisibility("System.HasAddon(pvr.iptvsimple)"):
        xbmc.executebuiltin("InstallAddon(pvr.iptvsimple)", True)
        if not xbmc.getCondVisibility("System.HasAddon(pvr.iptvsimple)"):
            return notify("Install PVR IPTV Simple Client first", error=True)
    m3u = base_url() + "/playlist.m3u"
    epg = base_url() + "/epg.xml"
    try:
        iptv = xbmcaddon.Addon("pvr.iptvsimple")
        for k, v in (("m3uPathType", "1"), ("m3uUrl", m3u), ("m3uCache", "false"),
                     ("epgPathType", "1"), ("epgUrl", epg), ("epgCache", "false"),
                     ("logoFromEpg", "1"), ("m3uRefreshMode", "1"),
                     ("m3uRefreshIntervalMins", "60")):
            iptv.setSetting(k, v)
        xbmc.executebuiltin("EnableAddon(pvr.iptvsimple)")
    except Exception as e:
        log("couldn't write IPTV Simple settings: {}".format(e))
    xbmcgui.Dialog().ok(
        "IPTV Simple Client",
        "Restart Kodi. If channels or the guide are missing, open IPTV Simple > Configure > "
        "the configuration marked [Enabled], and set (Location = Remote path):\n"
        "General > M3U playlist URL: {}\nEPG > XMLTV URL: {}".format(m3u, epg))


# ---------------------------------------------------------------- router
ROUTES_NEED_TABLO = {
    "channels": lambda t, a: channels(t),
    "play_live": lambda t, a: play_live(t, a["id"]),
    "recordings": lambda t, a: recordings(t),
    "episodes": lambda t, a: episodes(t, a["show"]),
    "play_rec": lambda t, a: play_rec(t, a["path"], a.get("pos")),
    "mark": lambda t, a: mark(t, a["path"], a["watched"]),
    "protect": lambda t, a: protect(t, a["path"], a["on"]),
    "delete": lambda t, a: delete(t, a["path"]),
    "delete_watched": lambda t, a: delete_watched(t, a["show"]),
    "upcoming": lambda t, a: upcoming(t),
    "shows": lambda t, a: shows(t, a.get("q", "")),
    "search": lambda t, a: search(t),
    "rules": lambda t, a: rules(t),
    "series": lambda t, a: series(t, a["path"], a.get("title", "")),
    "set_rule": lambda t, a: set_rule(t, a["path"], a["rule"]),
    "sched_airing": lambda t, a: sched_airing(t, a["path"], a["on"]),
    "status": lambda t, a: status(t),
    "refresh": lambda t, a: refresh(t),
    "diag": lambda t, a: diag(t),
}


def run(argv=None):
    global HANDLE, BASE
    argv = argv or sys.argv
    BASE = argv[0]
    HANDLE = int(argv[1]) if len(argv) > 1 and argv[1].lstrip("-").isdigit() else -1
    args = dict(parse_qsl(argv[2][1:] if len(argv) > 2 and argv[2] else ""))
    action = args.get("action")
    log("plugin action={} args={}".format(action, {k: v for k, v in args.items() if k != "action"}))
    if not action:
        return root()
    if action == "settings":
        return addon().openSettings()
    if action == "setup_iptv":
        return setup_iptv()
    if action == "shows_menu":
        return shows_menu()
    if action == "noop":
        return
    fn = ROUTES_NEED_TABLO.get(action)
    if not fn:
        return
    tablo = get_tablo()
    try:
        fn(tablo, args)
    except AuthError as e:
        notify(str(e), error=True)
        if HANDLE >= 0 and action not in ("play_live", "play_rec"):
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        addon().openSettings()
    except Exception as e:
        log("{} failed: {}".format(action, e), xbmc.LOGERROR)
        notify(str(e), error=True)
        if action in ("play_live", "play_rec"):
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        elif HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
