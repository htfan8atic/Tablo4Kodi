# -*- coding: utf-8 -*-
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from .tablo import Tablo

ADDON_ID = "plugin.video.tablo4g"


def addon():
    return xbmcaddon.Addon(ADDON_ID)


def setting(key):
    return addon().getSetting(key)


def setting_bool(key):
    return addon().getSetting(key).lower() == "true"


def setting_int(key, default=0):
    try:
        return int(addon().getSetting(key))
    except ValueError:
        return default


def profile_dir():
    p = xbmcvfs.translatePath(addon().getAddonInfo("profile"))
    if not os.path.isdir(p):
        os.makedirs(p)
    return p


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[{}] {}".format(ADDON_ID, msg), level)


def notify(msg, error=False):
    xbmcgui.Dialog().notification(
        "Tablo", msg,
        xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO, 5000)


def get_tablo():
    return Tablo(
        email=setting("email"),
        password=setting("password"),
        state_file=os.path.join(profile_dir(), "state.json"),
        device_url_override=setting("device_ip"),
        device_name=setting("device_name"),
        logger=log,
    )


def server_port():
    return setting_int("port", 18885) or 18885


def base_url():
    return "http://127.0.0.1:{}".format(server_port())
