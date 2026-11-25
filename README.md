# Tablo 4th Gen Video & PVR Add-on for Kodi (Unofficial)

**[⬇ Download the latest release](https://github.com/htfan8atic/Tablo4Kodi/releases/latest)** (v1.2.0 beta) ·
[Setup](#setup) · [What's new](#whats-new-in-120) · [Troubleshooting](#troubleshooting) ·
[Report a problem](https://github.com/htfan8atic/Tablo4Kodi/issues)

Watch live TV, browse a full grid TV guide, record and manage recordings from a **Tablo 4th Gen** DVR, all inside Kodi.

- **Live TV and guide** appear in Kodi's own **TV** section (Channels and Guide), through *PVR IPTV Simple Client*.
- **Record from the guide:** press **OK** on any upcoming program and choose *this episode*, *new episodes* or *all episodes*.
- **Video add-on** (Add-ons → Video add-ons → Tablo (4th Gen)) for recordings, upcoming recordings, series rules and Tablo status.

**Requirements:** Kodi 19 or newer (tested on Kodi 22 for Windows and LibreELEC), a Tablo 4th Gen already set up in the official Tablo app, and the Kodi device on the same home network as the Tablo. Older (2nd/3rd Gen) Tablos aren't supported.

## What's new in 1.2.0

- **Record with OK in the guide.** Press OK on a future program on a Tablo channel to open **Record with Tablo** directly. OK on a program that's on now still tunes to it.
- **Reliable guide recording.** Record with Tablo now finds future airings and movies, puts **Record this episode only** first, and shows the airing's day and time.
- **All your channels.** Channels the Tablo found in its scan but Tablo's online lineup misses (for example a local FOX or PBS) are now added, with their guide listings.
- **Backup logos** for channels Tablo has no logo for (Buzzr, MeTV, Comet, Create and more).
- **Guide updates show up right away**, without restarting Kodi.
- **Smoother updates:** no more "Address already in use" error after installing a new version.

Full details: [release notes](https://github.com/htfan8atic/Tablo4Kodi/releases/latest).

## Setup

### Before you start

1. Find your Tablo's IP address in the Tablo app's settings (iOS or Android), or in your router's list of connected devices.
2. Recommended: turn on **address reservation** (DHCP reservation / fixed IP) for the Tablo in your router, so its address doesn't change after a power cut or firmware update.
3. Check it answers: on a Windows PC, press Windows key + R, type `cmd`, press Enter, and run `ping <Tablo IP>`. You should get replies.

### 1. Install

1. In Kodi: Settings → System → Add-ons → turn on **Unknown sources**.
2. Download `plugin.video.tablo4g-<version>.zip` from the [latest release](https://github.com/htfan8atic/Tablo4Kodi/releases/latest). In Kodi go to Settings → Add-ons → **Install from zip file** and select it.
3. Install **PVR IPTV Simple Client** from the Kodi add-on repository (under PVR clients) if you don't have it.
4. Optional, for pause and rewind on live TV: install **Inputstream FFmpeg Direct** and **InputStream Adaptive**.

To update later, install the newer ZIP the same way. Your settings are kept.

### 2. Sign in

1. Open the Tablo add-on's **Settings**.
2. Enter your Tablo account **email** and **password**.
3. **Tablo IP address override:** enter your Tablo's IP, for example `192.168.1.50`. Tablo's online service sometimes reports an old address, so this is recommended. You don't need to add a port; the add-on uses the right one (8887).
4. Restart Kodi, open the add-on and run **Test connection**. Every line should say OK.

| Test connection line | If it fails |
|---|---|
| Cloud sign-in | Wrong email or password, or no internet |
| Tablo answers at … | Wrong IP, or Kodi isn't on the Tablo's network |
| Tablo on LAN | Enter just the IP (or `IP:8887`) |
| Local service | Restart Kodi. HTTP 503 means the guide is still being built; wait a minute |

### 3. Connect IPTV Simple (channels and guide)

1. Settings → Add-ons → My add-ons → PVR clients → **PVR IPTV Simple Client** → **Configure**.
2. Choose the configuration marked **[Enabled]** (often "Migrated Add-on Config"). Don't add a new one.
3. **General:** Location = *Remote path*, M3U playlist URL = `http://127.0.0.1:18885/playlist.m3u`
4. **EPG:** Location = *Remote path*, XMLTV URL = `http://127.0.0.1:18885/epg.xml`
5. Optional, **Timeshift:** enable it for pause and rewind (needs Inputstream FFmpeg Direct).
6. Press OK and restart Kodi. Channels and the guide fill in within a minute or two.

The add-on's **Set up IPTV Simple Client** item tries to do steps 3–4 for you, but on Kodi 20 and newer you usually have to enter them by hand.

### 4. One Kodi setting

Settings → PVR & Live TV → Guide → **Default select action**: set it to *Switch to channel* (or *Smart select*). This makes OK on a program that's on now tune to it, while OK on a future program records with Tablo. Don't set it to *Record*: Kodi's own recording doesn't work with Tablo channels.

## Using it

| To… | Go to |
|---|---|
| Watch live TV | Home → TV → Channels |
| Browse the guide | Home → TV → Guide |
| Record from the guide | TV → Guide → **OK** on a future program (or context menu → **Record with Tablo**) |
| Play, protect or delete recordings | Tablo add-on → Recordings (context menu for actions) |
| Search for a show to record | Tablo add-on → Record a show |
| See what's scheduled and conflicts | Tablo add-on → Upcoming recordings |
| Manage series recordings | Tablo add-on → Series recording rules |
| Tuners and storage | Tablo add-on → Tablo status |
| Update the guide now | Tablo add-on → Refresh TV guide now |

### Recording from the TV guide

Highlight a program that hasn't started yet on a Tablo channel and press **OK** (Enter on a keyboard, Select on a remote). The **Record with Tablo** menu opens:

1. **Record this episode only** (or *Record this airing* for movies)
2. **Record new episodes only**
3. **Record all episodes**
4. Cancel options, when something is already scheduled

The menu title shows the airing's day and time so you can check it's the right one. You can also open the context menu on any program (right-click, press **C**, or long-press OK) and choose **Record with Tablo**.

- OK on a program that's **on now** switches to the channel as usual.
- **Other TV sources** (e.g. HDHomeRun channels) aren't affected.
- A **mouse click** keeps Kodi's normal behaviour; right-click → Record with Tablo instead.
- **Turn it off** in the add-on's Settings → *Live TV & guide* → **OK on a future programme in the TV guide records with Tablo**. While it's on, the add-on adds a small key mapping (`userdata/keymaps/tablo4g_guide.xml`) that only applies in the TV guide. It's separate from your own keymaps, and it's removed whenever the add-on stops, is disabled or is uninstalled.

### Channels and guide

- The add-on refreshes the guide when Kodi starts and every 6 hours, so normally there's nothing to do. **Refresh TV guide now** forces an update.
- **Settings → Live TV & guide** sets how many days of guide to load (up to 14), how often to refresh, and whether to include Tablo's free streaming (FAST) channels.
- **Channels missing from Tablo's online lineup** are added from the Tablo's own channel scan, with listings from Tablo's online guide or, if it has none, from the guide stored on the Tablo.

### Channel logos

- By default, channels show the full-colour logo Tablo provides, as in the Tablo apps. **Settings → Live TV & guide → Channel logos** can instead make them *Same size* (trimmed to line up) or *Same size, white*.
- **Backup logos:** for channels Tablo has no logo for, or only broken ones, the add-on uses a logo from the community [tv-logos](https://github.com/tv-logo/tv-logos) collection, matched by channel name. Subchannels named only by a station code (e.g. WSBDT4) stay blank rather than show the wrong logo. Turn this off under **Settings → Live TV & guide → Backup logos**.
- To set a logo yourself: Kodi Settings → PVR & Live TV → General → **Channel manager** → choose the channel → **Channel icon**.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Guide rows stay empty for some channels | Kodi keeps its own copy of the guide. Settings → PVR & Live TV → Guide → **Clear data**. Kodi reloads it from the add-on in a few seconds; recordings and channels aren't affected. |
| OK on a future program just tunes | Check the setting is on (Settings → Live TV & guide). On Kodi, set *Default select action* to *Switch to channel*. If your remote's OK sends an unusual key, report it with a log. |
| "Couldn't find … at that time on the Tablo" | Run **Refresh TV guide now** and try again. Some sports events can't be matched; use **Record a show** for those. |
| A channel the Tablo app shows is missing | Run **Refresh TV guide now**. If it's still missing, rescan channels in the Tablo app, then refresh again. |
| A channel has no logo | Tablo has none for it and the backup collection doesn't either. Set one in Kodi's Channel manager (above). |
| "Playback failed" / "Can't reach the Tablo" | Check the IP override is the Tablo's current IP, then run Test connection. |
| Tablo on LAN: Authentication failure | Enter just the IP, or `IP:8887`. |
| Channels but an empty guide | Set the XMLTV URL in the **[Enabled]** IPTV Simple configuration. |
| No channels in TV | Set the M3U URL (setup step 3) and restart Kodi. |
| "Address already in use" after an update | Restart Kodi once (fixed from 1.0.2 on). |
| Stopped working after a Tablo update | Tablo may have changed something; report it with a log. |

**Kodi log:** Windows `%APPDATA%\Kodi\kodi.log` · LibreELEC/CoreELEC `/storage/.kodi/temp/kodi.log` · Android/Fire TV `Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log` · Linux `~/.kodi/temp/kodi.log` · Mac `~/Library/Logs/kodi.log`. Lines starting `[plugin.video.tablo4g]` are the useful ones. Your email is masked in the log; your Tablo's local IP isn't.

## LibreELEC and CoreELEC

The add-on is plain Python, so the same ZIP and steps work on LibreELEC and CoreELEC (tested on LibreELEC with Kodi 22). Differences:

- **Log file:** `/storage/.kodi/temp/kodi.log`, or the network share `\\<box IP>\Logfiles`. On LibreELEC, **LibreELEC Settings → System → Logs** can upload it and give you a link.
- **Raspberry Pi 4:** no hardware MPEG-2 decoding, and Tablo's antenna channels are MPEG-2, so 1080i channels may stutter. A Pi 5, an x86 box or a CoreELEC (Amlogic) box handles them fine.
- **Time zone:** set it under Settings → Interface → Regional; the guide follows the device's clock.

## Using it alongside HDHomeRun or another TV source

Kodi can run several TV sources at once, so IPTV Simple (Tablo) and an HDHomeRun or other PVR client can both stay enabled; they don't share tuners. On the same antenna, each local channel appears twice.

- **Channel groups:** TV → Channels → side menu → select a group. Tablo channels are in the **Antenna** group.
- **Hide duplicates:** TV → Channels → context menu → **Channel manager** → uncheck **Visible**.
- **One at a time:** disable either client under Add-ons → My add-ons → PVR clients.

## Known limits

- Kodi's own *Record* doesn't work for Tablo channels (IPTV Simple can't record); use **Record with Tablo** or **Record a show**.
- Some sports events can't be matched from the guide; use **Record a show**.
- Recording thumbnails may not load.
- Your password is stored in plain text in Kodi's add-on settings, as with most Kodi add-ons. It's only sent to Tablo's sign-in service.
- Unofficial; not affiliated with Nuvyyo/Tablo. A Tablo firmware update may break it.

## How it works and credits

Sign-in, the channel lineup and most guide listings come from Tablo's online service (`lighthousetv.ewscloud.com`). Live streams, recordings, scheduling, the Tablo's own channel scan and its stored guide come directly from the Tablo on your network, using the same signed requests as the official apps.

Based on the MIT-licensed [tablo-api](https://github.com/trevor-viljoen/tablo-api) and [tablo2plex](https://github.com/hearhellacopters/tablo2plex), and the [unofficial legacy API docs](https://jessedp.github.io/tablo-api-docs/). Backup channel logos come from [tv-logos](https://github.com/tv-logo/tv-logos) by tv-logo (free for personal use; the logos are trademarks of their owners). MIT licensed, see LICENSE.txt.
