# Tablo 4th Gen Video & PVR Add-on for Kodi (Unofficial)

**[⬇ Download the latest release](https://github.com/htfan8atic/Tablo4Kodi/releases/latest)** (beta) ·
[Setup steps](#before-you-start) · [Report a problem](https://github.com/htfan8atic/Tablo4Kodi/issues)

Live TV, a grid TV guide, recordings and recording scheduling for **Tablo 4th Gen** DVRs in Kodi.

- **Live TV + guide** appear in Kodi's own **TV** section, through *PVR IPTV Simple Client*.
- **Video add-on** (Add-ons → Video add-ons → Tablo (4th Gen)) for recordings, scheduling and status.

Needs Kodi 19 or newer (tested on Kodi 22 for Windows and LibreELEC; should also work on CoreELEC, see below), a Tablo 4th Gen already set up in the official Tablo app, and the Kodi device on the same home network as the Tablo.
Older (2nd/3rd Gen) Tablos are not supported.

## Before you start

1. Find your Tablo's IP address in your router's or mesh app's list of connected devices. Or, more easily, in the settings of the Tablo app for iOS or Android.
2. Turn on **address reservation** (DHCP reservation / fixed IP) for it in that same app (recommended, as your Tablo's IP address could change after a firmware update, power failure, etc.).
3. From a computer on the same network, open Command Prompt (press Windows key + R, type `cmd`, press Enter) and run `ping <Tablo IP>`. You should get replies.

Current 4th Gen firmware takes the add-on's requests on **port 8887**. You don't need to type it: the add-on adds the right port when you enter just the IP.

## 1. Install

1. Settings → System → Add-ons → turn on **Unknown sources**.
2. Download `plugin.video.tablo4g-<version>.zip` from the [latest release](https://github.com/htfan8atic/Tablo4Kodi/releases), then in Kodi go to Settings → Add-ons → **Install from zip file** and select it.
3. Install **PVR IPTV Simple Client** from the Kodi Add-on repository (PVR clients) if you don't have it.
4. Optional, for pause/rewind on live TV: install **Inputstream FFmpeg Direct** and **InputStream Adaptive**.

To update, install a newer ZIP file the same way (your settings are kept), then restart Kodi.

## 2. Sign in

1. Open the video add-on's **Settings**.
2. Enter your Tablo account **email** and **password**.
3. **Tablo IP address override:** your Tablo's IP, for example `192.168.68.34`. Recommended: Tablo's cloud sometimes reports an old address. (`192.168.68.34:8887` works too.)
4. Restart Kodi, open the add-on, run **Test connection**. The sign-in, channel list, *Tablo on LAN* and *Local service* lines should say OK.

| Test connection line | If it fails |
|---|---|
| Cloud sign-in | Wrong email/password, or no internet |
| Tablo answers at … | Wrong IP, or Kodi isn't on the Tablo's network |
| Tablo on LAN | Wrong port: enter just the IP, or `IP:8887` |
| Local service | Restart Kodi. HTTP 503 means the guide isn't built yet; wait a minute |

## 3. Connect IPTV Simple (channels + guide)

1. Settings → Add-ons → My add-ons → PVR clients → PVR IPTV Simple Client → **Configure**.
2. Choose the configuration marked **[Enabled]** (often "Migrated Add-on Config"). Don't add a new one.
3. **General:** Location = *Remote path*, M3U playlist URL = `http://127.0.0.1:18885/playlist.m3u`
4. **EPG:** Location = *Remote path*, XMLTV URL = `http://127.0.0.1:18885/epg.xml`
5. Optional, **Timeshift**: enable it for pause/rewind (needs Inputstream FFmpeg Direct).
6. OK, then restart Kodi. The guide fills in within a minute.

The add-on's **Set up IPTV Simple Client** menu item tries to do steps 3–4 for you, but on Kodi 20+ you usually have to enter them by hand.

## Using it

| To… | Go to |
|---|---|
| Watch live TV | Home → TV → Channels |
| Grid guide | Home → TV → Guide |
| Recordings (play, protect, delete) | Video add-on → Recordings (use the context menu for actions) |
| Record a show | Video add-on → Record a show |
| Record from the guide | TV → Guide → **OK** on a future program, or context menu → **Record with Tablo** (see below) |
| What's scheduled / conflicts | Video add-on → Upcoming recordings |
| Series being recorded | Video add-on → Series recording rules |
| Tuners and storage | Video add-on → Tablo status |

**Recording from the TV guide:** in Home → TV → Guide, highlight a program that hasn't started yet on a Tablo channel and press **OK** (Enter on a keyboard, Select on a remote). The **Record with Tablo** menu opens: record this episode only, new episodes only, or all episodes, or cancel a recording. The menu title shows the airing's day and time, so you can check it picked the right one. Pressing OK on a program that's on now still switches to that channel, and channels from other back-ends (e.g. HDHomeRun) aren't affected. You can also open the context menu on any program (right-click, press **C**, or long-press OK) and choose **Record with Tablo**.

- Leave Kodi's Settings → PVR & Live TV → Guide → **Default select action** at *Switch to channel* (or *Smart select*), so OK on a current program tunes. Don't set it to *Record*: Kodi's own Record doesn't work for Tablo channels (IPTV Simple can't record).
- A mouse click on a future program keeps Kodi's normal behaviour; use right-click → **Record with Tablo**.
- To turn OK-to-record off, use the add-on's Settings → *Live TV & guide* → **OK on a future programme in the TV guide records with Tablo**. The add-on adds a small key mapping (`userdata/keymaps/tablo4g_guide.xml`) for this while it's running and removes it when it stops, disabled or uninstalled.

**Guide updates:** the add-on refreshes the guide by itself when Kodi starts and every 6 hours, so there's normally nothing to do. **Refresh TV guide now** in the add-on forces one. The add-on's Settings → *Live TV & guide* also sets how many days of guide to load (up to 14), how often to refresh, and whether to include Tablo's free streaming (FAST) channels.

**Channel logos:** by default the add-on shows each channel's logo as Tablo supplies it (the full-color versions the Tablo apps use, falling back to another version when one is missing). Under the add-on's Settings → *Live TV & guide* → **Channel logos** you can instead choose *Same size* (trimmed and resized so they line up) or *Same size, white* (white logos vanish on light skins). When the logos change, the add-on reloads IPTV Simple so Kodi shows them right away.

## Troubleshooting

| Symptom | Fix |
|---|---|
| A channel the Tablo app shows is missing in Kodi | The add-on adds channels from the Tablo's own scan when Tablo's online lineup lacks them. Run **Refresh TV guide now**; if it's still missing, rescan channels in the Tablo app, then refresh again. The add-on gets listings for these channels from Tablo's online guide where it can, otherwise from the guide stored on your Tablo; they have no logo. |
| "Playback failed" / "Can't reach the Tablo" | Check the IP override (the Tablo's current IP), run Test connection |
| Tablo on LAN: Authentication failure | Enter just the IP, or `IP:8887` |
| A channel has no logo | Tablo's server has no logo for that station (e.g. Telemundo); nothing to fix |
| Channels but empty guide | Set the XMLTV URL in the **[Enabled]** IPTV Simple configuration |
| No channels in TV | Set the M3U URL (step 3), restart Kodi |
| Stopped working after a Tablo update | Tablo may have changed its API; report it with a log |

Kodi log: Windows `%APPDATA%\Kodi\kodi.log` · Android/Fire TV `Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log` · Linux `~/.kodi/temp/kodi.log` · Mac `~/Library/Logs/kodi.log`. Lines starting `[plugin.video.tablo4g]` are the useful ones. Your email is masked in the log; your Tablo's local IP is not.

## LibreELEC and CoreELEC

The add-on is plain Python, so the same ZIP file and steps work on LibreELEC and CoreELEC (tested on LibreELEC with Kodi 22). The Tablo sends antenna channels as MPEG-2 video with Dolby Digital audio. Its dependencies come from the official Kodi repository. Differences:

- **Log file:** `/storage/.kodi/temp/kodi.log`. From another computer, use the network share `\\<box IP>\Logfiles`. On LibreELEC, **LibreELEC Settings → System → Logs** can upload it and give you a link.
- **Raspberry Pi 4:** no hardware MPEG-2 decoding, and antenna channels are often MPEG-2, so 1080i channels may stutter. A Pi 5, an x86 box or a CoreELEC (Amlogic) box handles them fine.
- **Time zone:** set it under Settings → Interface → Regional; the guide is built from the device's date.
- **Same network:** the box must be on the Tablo's network. Use the same Tablo IP override.

## Using it alongside HDHomeRun or another TV source

Kodi can run several TV sources at once, so IPTV Simple (Tablo) and an HDHomeRun or other PVR client can both stay enabled; they don't share tuners. On the same antenna, each local channel appears twice.

- **Channel groups:** TV → Channels → side menu → select a group. Tablo channels are in the **Antenna** group.
- **Hide duplicates:** TV → Channels → context menu → **Channel manager** → uncheck **Visible**.
- **Order and numbering:** Settings → PVR & Live TV (option names vary between Kodi versions).
- **One at a time:** disable either client under Add-ons → My add-ons → PVR clients.

## Known limits

- Kodi's own *Record* in the TV guide doesn't work for Tablo channels (IPTV Simple can't record). Use **Record with Tablo** from the guide's context menu, or **Record a show** in the add-on.
- **Record with Tablo** matches the program by show, channel, date and time; some sports events can't be matched. Use **Record a show** for those.
- Recording thumbnails may not load.
- Your password is stored in plain text in Kodi's add-on settings, as with most Kodi add-ons. It's only sent to Tablo's sign-in service.
- Unofficial; not affiliated with Nuvyyo/Tablo. A Tablo firmware update may break it.

## How it works / credits

Sign-in, channel list and guide come from Tablo's cloud (`lighthousetv.ewscloud.com`). Live streams, recordings and scheduling go directly to the Tablo on your network, using the same signed requests as the official apps. Based on the MIT-licensed [tablo-api](https://github.com/trevor-viljoen/tablo-api) and [tablo2plex](https://github.com/hearhellacopters/tablo2plex), and the [unofficial legacy API docs](https://jessedp.github.io/tablo-api-docs/). MIT licensed, see LICENSE.txt.
