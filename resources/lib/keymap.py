# -*- coding: utf-8 -*-
"""Optional keymap: OK / Enter in Kodi's TV guide runs the add-on's guide-click handler.

The handler opens Record with Tablo for a *future* programme on a Tablo channel and otherwise
sends Kodi's normal Select action, so current programmes still tune and other PVR back-ends
(e.g. HDHomeRun) behave as before. The file is removed whenever the service stops, so a
disabled or uninstalled add-on never leaves a key pointing at a missing script."""
import os

import xbmc
import xbmcvfs

from .kodiutils import addon, log

FILE = "tablo4g_guide.xml"
ADDON_ID = "plugin.video.tablo4g"


def _path():
    return os.path.join(xbmcvfs.translatePath("special://profile/keymaps/"), FILE)


def _script():
    special = "special://home/addons/{}/context.py".format(ADDON_ID)
    if os.path.exists(xbmcvfs.translatePath(special)):
        return special
    return os.path.join(xbmcvfs.translatePath(addon().getAddonInfo("path")), "context.py").replace("\\", "/")


def content():
    cmd = 'RunScript("{}",guideclick)'.format(_script())
    keys = lambda names: "".join("      <{0}>{1}</{0}>\n".format(n, cmd) for n in names)
    return ("<!-- Written by the Tablo (4th Gen) add-on; removed when it stops. "
            "Turn off under the add-on's settings, Guide. -->\n"
            "<keymap>\n  <tvguide>\n    <keyboard>\n" + keys(("return", "enter")) +
            "    </keyboard>\n    <remote>\n" + keys(("select", "enter")) +
            "    </remote>\n  </tvguide>\n</keymap>\n")


def sync(enabled):
    """Write or remove the keymap; reload Kodi's keymaps only if something changed."""
    p = _path()
    try:
        with open(p) as f:
            current = f.read()
    except (IOError, OSError):
        current = None
    want = content() if enabled else None
    if current == want:
        return False
    try:
        if want is None:
            os.remove(p)
        else:
            d = os.path.dirname(p)
            if not os.path.isdir(d):
                os.makedirs(d)
            with open(p, "w") as f:
                f.write(want)
    except (IOError, OSError) as e:
        log("couldn't update the guide keymap {}: {}".format(p, e), xbmc.LOGWARNING)
        return False
    xbmc.executebuiltin("Action(reloadkeymaps)")
    log("guide OK-to-record keymap {}".format("installed" if want else "removed"))
    return True
