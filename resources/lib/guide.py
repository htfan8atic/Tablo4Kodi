# -*- coding: utf-8 -*-
"""Build the M3U channel list and XMLTV guide for IPTV Simple Client."""

import datetime
from xml.sax.saxutils import escape, quoteattr

UTC = datetime.timezone.utc


def parse_time(s):
    """Parse the cloud's ISO timestamps ('2025-04-20T14:00Z', '+00:00', fractions)."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    if "." in s:
        head, tail = s.split(".", 1)
        tz = ""
        for sep in ("+", "-"):
            if sep in tail:
                tz = sep + tail.split(sep, 1)[1]
                break
        s = head + tz
    # Python 3.8 fromisoformat needs seconds
    date, _, rest = s.partition("T")
    tz = ""
    for sep in ("+", "-"):
        if sep in rest:
            rest, tz = rest.split(sep, 1)[0], sep + rest.split(sep, 1)[1]
            break
    if rest.count(":") == 1:
        rest += ":00"
    dt = datetime.datetime.fromisoformat("{}T{}{}".format(date, rest, tz))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def xmltv_time(dt):
    return dt.astimezone(UTC).strftime("%Y%m%d%H%M%S +0000")


def build_m3u(channels, base_url):
    lines = ['#EXTM3U tvg-shift="0"']
    for i, c in enumerate(channels, 1):
        chno = c["number"] or str(1000 + i)
        group = "Antenna" if c["kind"] == "ota" else "FAST"
        name = "{} {}".format(c["number"], c["call_sign"]).strip()
        lines.append(
            '#EXTINF:-1 tvg-id={} tvg-chno={} tvg-name={} tvg-logo={} group-title={},{}'.format(
                quoteattr(c["id"]), quoteattr(chno), quoteattr(name),
                quoteattr(c["logo"]), quoteattr(group), name))
        lines.append("#KODIPROP:mimetype=application/vnd.apple.mpegurl")
        lines.append("{}/live/{}.m3u8".format(base_url, c["id"]))
    return "\n".join(lines) + "\n"


def _programme(a, channel_id):
    start = parse_time(a.get("datetime"))
    if not start:
        return None
    stop = start + datetime.timedelta(seconds=int(a.get("duration") or 0))
    show = a.get("show") or {}
    kind = a.get("kind")
    title = show.get("title") or a.get("title") or ""
    out = ['  <programme start="{}" stop="{}" channel={}>'.format(
        xmltv_time(start), xmltv_time(stop), quoteattr(channel_id))]
    out.append('    <title lang="en">{}</title>'.format(escape(title)))
    ep = a.get("episode") or {}
    if kind == "episode" and a.get("title") and a.get("title") != title:
        out.append('    <sub-title lang="en">{}</sub-title>'.format(escape(a["title"])))
    if a.get("description"):
        out.append('    <desc lang="en">{}</desc>'.format(escape(a["description"])))
    if a.get("genres"):
        for g in a["genres"]:
            out.append('    <category lang="en">{}</category>'.format(escape(g)))
    if kind == "movieAiring":
        out.append('    <category lang="en">Movie</category>')
        yr = (a.get("movieAiring") or {}).get("releaseYear")
        if yr:
            out.append("    <date>{}</date>".format(yr))
    elif kind == "sportEvent":
        out.append('    <category lang="en">Sports</category>')
    if kind == "episode":
        season = ep.get("season") or {}
        sn = season.get("number") if season.get("kind") == "number" else None
        en = ep.get("episodeNumber")
        if sn or en:
            out.append('    <episode-num system="xmltv_ns">{}.{}.</episode-num>'.format(
                (int(sn) - 1) if sn else "", (int(en) - 1) if en else ""))
        oad = ep.get("originalAirDate")
        if oad:
            out.append("    <date>{}</date>".format(oad.replace("-", "")))
            if oad[:10] != start.date().isoformat():
                out.append("    <previously-shown />")
        else:
            out.append("    <previously-shown />")
    q = a.get("qualifiers") or []
    if isinstance(q, list) and "new" in [str(x).lower() for x in q]:
        out.append("    <new />")
    imgs = a.get("images") or []
    if imgs:
        out.append("    <icon src={} />".format(quoteattr(imgs[0].get("url", ""))))
    rating = ep.get("rating") or (a.get("movieAiring") or {}).get("filmRating")
    if rating:
        out.append('    <rating><value>{}</value></rating>'.format(escape(rating)))
    out.append("  </programme>")
    return "\n".join(out)


def build_xmltv(channels, airings_by_channel):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<tv generator-info-name="plugin.video.tablo4g">']
    for c in channels:
        out.append('  <channel id={}>'.format(quoteattr(c["id"])))
        out.append('    <display-name>{}</display-name>'.format(
            escape("{} {}".format(c["number"], c["call_sign"]).strip())))
        if c["logo"]:
            out.append("    <icon src={} />".format(quoteattr(c["logo"])))
        out.append("  </channel>")
    now = datetime.datetime.now(UTC)
    for c in channels:
        seen = set()
        for a in airings_by_channel.get(c["id"], []):
            key = a.get("identifier") or a.get("datetime")
            if key in seen:
                continue
            seen.add(key)
            p = _programme(a, c["id"])
            if p and parse_time(a["datetime"]) + datetime.timedelta(
                    seconds=int(a.get("duration") or 0)) > now:
                out.append(p)
    out.append("</tv>")
    return "\n".join(out) + "\n"
