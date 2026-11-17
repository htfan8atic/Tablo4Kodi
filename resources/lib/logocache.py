# -*- coding: utf-8 -*-
"""Cache of uniform channel logos, served by the background service at /logo/<key>.png."""

import hashlib
import os

from . import logos

ORIGINAL, SAME_SIZE, WHITE = 0, 1, 2


def _key(url, mode):
    # The key changes when the logo URL or style changes, so Kodi's image cache never shows a stale one.
    return hashlib.sha1("{}|{}|v1".format(url, mode).encode("utf-8")).hexdigest()[:16]


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
    """Download and normalize any logos not cached yet. Returns how many were made."""
    if mode == ORIGINAL:
        return 0
    made = 0
    for c in channels:
        url = c.get("logo")
        if not url:
            continue
        p = path_for(profile, _key(url, mode))
        if os.path.exists(p):
            continue
        try:
            r = session.get(url, timeout=(4, 20))
            r.raise_for_status()
            try:
                data = logos.normalize(r.content, white=(mode == WHITE))
            except logos.Unsupported as e:
                log("logo {} kept as-is ({})".format(c.get("call_sign"), e))
                data = r.content
            tmp = p + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, p)
            made += 1
        except Exception as e:  # a missing logo must never break the guide
            log("logo {} failed: {}".format(c.get("call_sign"), e))
    return made


def apply(channels, profile, mode, base_url):
    """Point each channel's logo at the cached uniform version when it exists."""
    if mode == ORIGINAL:
        return channels
    for c in channels:
        url = c.get("logo")
        if url:
            key = _key(url, mode)
            if os.path.exists(path_for(profile, key)):
                c["logo"] = "{}/logo/{}.png".format(base_url, key)
    return channels
