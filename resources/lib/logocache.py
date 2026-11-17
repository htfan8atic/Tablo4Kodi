# -*- coding: utf-8 -*-
"""Cache of uniform channel logos, served by the background service at /logo/<key>.png."""

import hashlib
import os

from . import logos

ORIGINAL, SAME_SIZE, WHITE, TILE = 0, 1, 2, 3


def _key(urls, mode):
    # The key changes when the logo URLs or style change, so Kodi's image cache never shows a stale one.
    return hashlib.sha1("{}|{}|v4".format("|".join(urls), mode).encode("utf-8")).hexdigest()[:16]


def _candidates(c):
    return c.get("logos") or ([c["logo"]] if c.get("logo") else [])


def cache_dir(profile):
    d = os.path.join(profile, "logos")
    if not os.path.isdir(d):
        os.makedirs(d)
    return d


def path_for(profile, key):
    if not key.isalnum():  # only our own hex keys
        return None
    return os.path.join(cache_dir(profile), key + ".png")


def build(channels, session, profile, mode, log=lambda m: None):
    """Download and normalize any logos not cached yet, trying each logo version in turn.
    Returns how many were made. ORIGINAL keeps the image untouched (only the fallback applies)."""
    made = 0
    for c in channels:
        urls = _candidates(c)
        if not urls:
            continue
        p = path_for(profile, _key(urls, mode))
        if os.path.exists(p):
            continue
        for url in urls:
            try:
                r = session.get(url, timeout=(4, 20))
                r.raise_for_status()
            except Exception as e:  # missing on Tablo's CDN: try the next version
                log("logo {} not available at {} ({})".format(c.get("call_sign"), url, e))
                continue
            data = r.content
            if mode != ORIGINAL:
                try:
                    data = logos.normalize(r.content, white=(mode == WHITE), plate=(mode == TILE))
                except logos.Unsupported as e:
                    log("logo {} kept as-is ({})".format(c.get("call_sign"), e))
            tmp = p + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, p)
            made += 1
            break
    return made


def apply(channels, profile, mode, base_url):
    """Point each channel's logo at the cached version when it exists."""
    for c in channels:
        urls = _candidates(c)
        if urls:
            key = _key(urls, mode)
            if os.path.exists(path_for(profile, key)):
                c["logo"] = "{}/logo/{}.png".format(base_url, key)
    return channels
