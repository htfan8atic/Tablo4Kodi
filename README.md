# Tablo (4th Gen) for Kodi — unofficial

Live TV, a grid TV guide, recordings and recording scheduling for **Tablo 4th Gen** DVRs in Kodi.

- **Live TV + guide** appear in Kodi's own **TV** section, through *PVR IPTV Simple Client*.
- **Video add-on** (Add-ons → Video add-ons → Tablo (4th Gen)) for recordings, scheduling and status.

Needs Kodi 19 or newer (tested on Kodi 22 for Windows; should also work on LibreELEC and CoreELEC,
see below), a Tablo 4th Gen already set up in the
official Tablo app, and the Kodi device on the same home network as the Tablo.
Older (2nd/3rd Gen) Tablos are not supported.

## Before you start

1. Find your Tablo's IP address in your router's or mesh app's list of connected devices. Or, more easily in settings in the Tablo app for iOS or Google Play mobile device
2. Turn on **address reservation** (DHCP reservation / fixed IP) for it in that same app (recommended as your Tablo's IP address could change after a firmware update, power failure, etc.).
3. From a computer on the same network, opening Command Prompt (press Windows key + R, type cmd, press Enter) and running `ping <Tablo IP>` should get replies.

Current 4th Gen firmware takes the add-on's requests on **port 8887**.

## 1. Install

1. Settings → System → Add-ons → turn on **Unknown sources**.
2. Settings → Add-ons → **Install from zip file** → this zip.
3. Install **PVR IPTV Simple Client** from the Kodi Add-on repository (PVR clients) if you don't have it.
4. Optional, for pause/rewind on live TV: install **Inputstream FFmpeg Direct** and **InputStream Adaptive**.

To update, install a newer zip the same way (your settings are kept), then restart Kodi.

## 2. Sign in

1. Open the video add-on's **Settings**.
2. Enter your Tablo account **email** and **password**.
3. **Tablo IP address override:** `<your Tablo IP>:8887` (for example `192.168.68.34:8887`).
4. Restart Kodi, open the add-on, run **Test connection**. Every line should say OK.

| Test connection line | If it fails |
|---|---|
| Cloud sign-in | Wrong email/password, or no internet |
| Tablo answers at … | Wrong IP, or Kodi isn't on the Tablo's network |
| Tablo on LAN | Wrong port. Use `:8887` |
| Local service | Restart Kodi. HTTP 503 means use **Refresh TV guide now** |

## 3. Connect IPTV Simple (channels + guide)

1. Settings → Add-ons → My add-ons → PVR clients → PVR IPTV Simple Client → **Configure**.
2. Choose the configuration marked **[Enabled]** (often "Migrated Add-on Config"). Don't add a new one.
3. **General:** Location = *Remote path*, M3U playlist URL = `http://127.0.0.1:18885/playlist.m3u`
4. **EPG:** Location = *Remote path*, XMLTV URL = `http://127.0.0.1:18885/epg.xml`
5. Optional, **Timeshift**: enable it for pause/rewind (needs Inputstream FFmpeg Direct).
6. OK, then restart Kodi. The guide fills in within a minute.

The add-on's **Set up IPTV Simple Client** menu item tries to do steps 3–4 for you, but on Kodi 20+
you usually have to enter them by hand.

## Using it

| To… | Go to |
|---|---|
| Watch live TV | Home → TV → Channels |
| Grid guide | Home → TV → Guide |
| Recordings (play, protect, delete) | Video add-on → Recordings (use the context menu for actions) |
| Record a show | Video add-on → Record a show |
| What's scheduled / conflicts | Video add-on → Upcoming recordings |
| Tuners and storage | Video add-on → Tablo status |

**Channel logos:** by default the add-on makes every channel logo the same size and white, so they
line up neatly in Kodi's TV section. Change it under the add-on's Settings → *Live TV & guide* →
**Channel logos** (*Original*, *Same size*, or *Same size, white*). Kodi picks up the new logos at the
next guide refresh; use **Refresh TV guide now** and restart Kodi to see them straight away.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Playback failed" / "Can't reach the Tablo" | Check the IP override (`<IP>:8887`), run Test connection |
| Tablo on LAN: Authentication failure | Use port `:8887` |
| Channels but empty guide | Set the XMLTV URL in the **[Enabled]** IPTV Simple configuration |
| No channels in TV | Set the M3U URL (step 3), restart Kodi |
| Stopped working after a Tablo update | Tablo may have changed its API; report it with a log |

Kodi log: Windows `%APPDATA%\Kodi\kodi.log` · Android/Fire TV
`Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log` · Linux `~/.kodi/temp/kodi.log` · Mac
`~/Library/Logs/kodi.log`. Lines starting `[plugin.video.tablo4g]` are the useful ones. Your
email is masked in the log; your Tablo's local IP is not.

## LibreELEC and CoreELEC

The add-on is plain Python, so the same zip and steps work on LibreELEC 12 and CoreELEC 21 (both
Kodi 21). Its dependencies come from the official Kodi repository. Differences:

- **Log file:** `/storage/.kodi/temp/kodi.log`. From another computer, use the network share
  `\\<box IP>\Logfiles`. On LibreELEC, **LibreELEC Settings → System → Logs** can upload it and give you a link.
- **Raspberry Pi 4:** no hardware MPEG-2 decoding, and antenna channels are often MPEG-2, so 1080i
  channels may stutter. A Pi 5, an x86 box or a CoreELEC (Amlogic) box handles them fine.
- **Time zone:** set it under Settings → Interface → Regional; the guide is built from the box's date.
- **Same network:** the box must be on the Tablo's network. Use the same `<Tablo IP>:8887` override.

## Using it alongside HDHomeRun or another TV source

Kodi can run several TV sources at once, so IPTV Simple (Tablo) and an HDHomeRun or other PVR client
can both stay enabled; they don't share tuners. On the same antenna, each local channel appears twice.

- **Channel groups:** TV → Channels → side menu → pick a group. Tablo channels are in the **Antenna** group.
- **Hide duplicates:** TV → Channels → context menu → **Channel manager** → untick **Visible**.
- **Order and numbering:** Settings → PVR & Live TV (option names vary between Kodi versions).
- **One at a time:** disable either client under Add-ons → My add-ons → PVR clients.

## Known limits

- You can't record from Kodi's TV guide (IPTV Simple doesn't support it). Use **Record a show** in the add-on.
- Recording thumbnails may not load.
- Your password is stored in plain text in Kodi's add-on settings, as with most Kodi add-ons. It's only sent to Tablo's sign-in service.
- Unofficial; not affiliated with Nuvyyo/Tablo. A Tablo firmware update may break it.

## How it works / credits

Sign-in, channel list and guide come from Tablo's cloud (`lighthousetv.ewscloud.com`). Live
streams, recordings and scheduling go directly to the Tablo on your network, using the same signed
requests as the official apps. Based on the MIT-licensed
[tablo-api](https://github.com/trevor-viljoen/tablo-api) and
[tablo2plex](https://github.com/hearhellacopters/tablo2plex), and the
[unofficial legacy API docs](https://jessedp.github.io/tablo-api-docs/). MIT licensed, see LICENSE.txt.
