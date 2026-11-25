# -*- coding: utf-8 -*-
"""Backup channel logos for channels Tablo has no (working) logo for.

Logos come from the community tv-logos collection (https://github.com/tv-logo/tv-logos,
free for personal use, credited in the README). They're downloaded at run time like Tablo's
own logos; none are shipped with the add-on. A channel is matched by its name (call sign)
first, then by its network, the network only for a station's main channel (x.1), so a
subchannel named after its station (WSBDT4) never gets the main network's logo."""
import re

BASE = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-states/{}-us.png"

# file names in the collection's united-states folder (without "-us.png")
_STEMS = """
3abn-dare-to-dream-network 3abn-kids-network 3abn-latino-network 3abn-praise-him-music-network
3abn-proclaim-network 3abn a-and-e abc-live-event abc-localish abc-news-live-event
abc-news-live abc-news-livestream-coverage abc-news abc acc-network-extra acc-network
accuweather action-channel adult-swim africa-channel afro akc-tv altitude-sports
ambient-channel amc american-heroes-channel animal-planet anime-network antenna aspire-tv
at-and-t-sportsnet awe axs-tv azteca-america baby-first-tv baby-tv bally-sports-arizona-extra
bally-sports-arizona-plus bally-sports-arizona bally-sports-detroit-plus bally-sports-detroit
bally-sports-florida-plus bally-sports-florida bally-sports-great-lakes
bally-sports-indiana-plus bally-sports-indiana bally-sports-kansas-city-plus
bally-sports-kansas-city bally-sports-midwest-plus bally-sports-midwest
bally-sports-new-orleans-plus bally-sports-new-orleans bally-sports-north-extra
bally-sports-north-plus bally-sports-north bally-sports-ohio-plus bally-sports-ohio
bally-sports-oklahoma-plus bally-sports-oklahoma bally-sports-san-diego-plus
bally-sports-san-diego bally-sports-socal-plus bally-sports-socal bally-sports-south-plus
bally-sports-south bally-sports-southeast-plus bally-sports-southeast
bally-sports-southwest-plus bally-sports-southwest bally-sports-sun-plus bally-sports-sun
bally-sports bally-sports-west-plus bally-sports-west bally-sports-wisconsin-plus
bally-sports-wisconsin bangu bbc-america beauty-channel bein-sports-2 bein-sports-3
bein-sports-4 bein-sports-5 bein-sports-6 bein-sports-7 bein-sports-8 bein-sports-espanol
bein-sports bein-sports-xtra-espanol bein-sports-xtra bek-sports-plus bek-sports bet-gospel
bet-her bet-jams bet-soul bet big-ten-network binge-tv black-news-channel blaze-tv
bloomberg-live-events bloomberg-quicktake bloomberg-television boomerang bounce br-live bravo
brazzers-tv btn busted buy-tv buzzr byu-tv c-span-1 c-span-2 c-span-3 c-span-live cars-tv
cartoon-network cartoonito catchy-comedy cbn-news cbn cbs-news-24-7 cbs-news-baltimore
cbs-news-bay-area cbs-news-boston cbs-news-chicago cbs-news-colorado cbs-news-detroit
cbs-news-dfw-dallas-fort-worth cbs-news-los-angeles cbs-news-miami cbs-news-minnesota
cbs-news-new-york cbs-news-philly cbs-news-pittsburgh cbs-news-sacramento cbs-news cbs-nfl
cbs-sports-golazo-network cbs-sports-hq cbs-sports-network cbs-sports charge cheddar-news
cheddar cine-latino cine-sony cinemax-action cinemax-classics cinemax-en-espanol cinemax-hits
cinemax-max-go cinemax-moviemax cinemax-outermax cinemax-thrillermax cinemax circle
classic-arts-showcase cleo-tv cmc cmt-color cmt-music cmt cnbc cnbc-world cnn-airport cnn-max
cnn comedy-central comedy-tv comet cooking-channel cornerstone-network court-tv cowboy-channel
cowboy-way-channel cozi-tv create crime-and-investigation cw-sports cw dabl daystar dazn defy
destination-america discovery-channel discovery-en-espanol discovery-familia discovery-family
discovery-history discovery-life discovery-science discovery-turbo disney-channel disney-jr
disney-plus disney-xd dog-tv dove-channel dove-kids e-entertainment ebony-tv el-rey epix-2
epix-drive-in epix-hits epix es-tv esne espn-2 espn-3 espn-accn-extra espn-accn
espn-bases-loaded espn-classic espn-college-extra espn-college-football espn-deportes
espn-goalline espn-monday-night-football espn-plus espn-saturday-night-football espn-sec espn-u
espn espnews et-live fanduel-racing fanduel-tv fave-tv fetv fight-network film-detective
filmrise-classics filmrise-crime filmrise-family filmrise-movies fite-tv flix fm
fmc-family-movie-classics fntsy-sports-network food-network fox-business fox-news fox-nfl
fox-soccer-plus fox-soul fox-sports-1 fox-sports-2 fox-sports-deportes fox-sports-go fox-sports
fox fox-weather free-speech-tv freeform fubo-cycling fubo-sports-network funimation fuse fusion
fx fxm-movie-channel fxx fyi g4 gac-family gac-living gaiam-tv galavision game-show-network
gem-shopping-network get-tv gol-tv great-american-country great-american-faith-and-living
great-american-family grit hallmark-channel hallmark-family hallmark-movies-now
hallmark-mystery hallmark-tv hapa hbo-comedy hbo-drama hbo-family hbo-films hbo-hits hbo-latino
hbo-max-color hbo-max hbo-movies hbo-on-demand hbo hdnet-movies heartland her-sphere hgtv
history-channel-2 history-channel history-en-espanol hitz-2 hitz-3 hitz hln hogar-de-hgtv home
hope-channel hsn-2 hsn hunt-channel hustler-hd hustler-tv ifc info-wars insp inspiration-tv
investigation-discovery ion-mystery ion-plus ion-television jtv justice-central-tv
kabillion-girls-rule kabillion key-tv kids-street klife laff latv law-and-crime-network
lifetime-movie-network lifetime-movies lifetime-real-women lifetime live-now-fox
live-well-network local-now logo longhorn-network magnolia-network marquee-sports-network
masn-2 masn me-tv-plus me-tv-toons me-tv mgm-plus-drive-in mgm-plus-hits mgm-plus-marquee
mgm-plus mgm-sci-fi military-history mlb-extra-innings mlb-network-strike-zone mlb-network
mls-direct-kick mls-logo monumental-sports-network motor-trend movie-plex movie-sphere-gold
movie-sphere movies ms-now msg-2 msg-plus-2 msg-plus msg msgsn-2 msgsn mtv-2 mtv-classic
mtv-live mtv-u mtv music-choice my-destination my-network-tv nasa-tv-globe-color
nasa-tv-globe-logo nasa-tv nat-geo-mundo nat-geo-wild national-geographic nautical-channel
nba-finals nba-league-pass-mls-direct-kick-combo nba-league-pass nba-tv nbc-13-weau nbc-13-who
nbc-14-wfie nbc-15-wmtv nbc-18-wlex nbc-25-week nbc-26-wagt nbc-26-wgba nbc-29-wvir
nbc-golf-channel nbc-golf nbc-lx nbc-nascar nbc-news-now nbc-news-online-only
nbc-olympics-summer-tokyo-2020 nbc-sports-chicago-plus-2 nbc-sports-chicago-plus
nbc-sports-chicago nbc-sports-engine nbc-sports-gold nbc-sports-live-extra nbc-sports
nbc-sunday-night-football nbc-true-crmz nbc-universo nbc nbcsn-bay-area nbcsn-boston
nbcsn-california nbcsn-chicago nbcsn-northwest nbcsn-philadelphia
nbcsn-premier-league-extra-time nbcsn-premier-league-live nbcsn nbcsn-washington necn nesn-plus
nesn news-nation news-net news12-brooklyn news12-connecticut news12-hudson-valley
news12-long-island news12-new-jersey news12-new-york news12-the-bronx news12-westchester
newsmax-tv newsmax2 newsnet-northern-michigan newsy next-level-sports nfl-game-pass nfl-network
nfl-red-zone nfl-thursday-night-football nhl-center-ice nhl-network nhl-on-espn nick-2 nick-jr
nick-music nick-night nick-on-demand nick-toons nick nickelodeon-en-espanol nickelodeon
nyc-tv-life olympic-channel one-america-news-network one-tv oprah-winfrey-network
outdoor-channel-plus outdoor-channel outer-sphere outlaw outside-tv ovation oxygen-true-crime
oxygen pac-12-arizona pac-12-bay-area pac-12-los-angeles pac-12-mountain pac-12-network
pac-12-oregon pac-12-washington paramount-network paramount-plus paramount-plus-with-showtime
pbs peachtree-tv penthouse-gold penthouse-quickies penthouse-tv people-tv pets-tv pga-tour-live
pixl playboy-tv plex-indieplex plex-movieplex-on-demand plex-movieplex plex-retroplex pop
popstar positiv primo-tv pursuit qubo quest qvc-2 qvc-3 qvc racer-network real-americas-voice
recipe-tv reelz retro-tv revolt rfd-tv ride-tv roar root-sports sbn screenpix-action screenpix
screenpix-voices screenpix-westerns scripps-news sec-network sho-bet shop-hq shop-lc shorts-tv
showtime-2 showtime-anywhere showtime-beyond showtime-boxing showtime-championship-boxing
showtime-extreme showtime-family-zone showtime-next showtime-on-demand showtime-ppv
showtime-showcase showtime-sports showtime showtime-women shudder smile-tv smithsonian-channel
sny so-yummy sony-movie-channel sony-movies soul-of-the-south-network space-city-home-network
spectrum-news-1 spectrum-news-13 spectrum-originals spectrum-sports spectrum-sportsnet-la
spectrum-sportsnet sportskool sportsman-channel sportsnet-pittsburgh
stadium-college-sports-atlantic stadium-college-sports-central stadium-college-sports-pacific
stadium start-tv starz-black starz-cinema starz-comedy starz-edge starz-encore-action
starz-encore-black starz-encore-classic starz-encore-espanol starz-encore-family
starz-encore-on-demand starz-encore-suspense starz-encore starz-encore-westerns starz-in-black
starz-kids-and-family starz-on-demand starz story-television sundance-tv syfy tastemade tbn tbs
tcm teen-nick telemundo-deportes telemundo telexitos tennis-channel tfc the-365
the-country-network the-cw the-first the-movie-channel the-movie-channel-xtra the-nest the-u
the-walk this-tv-network tlc tmz tnt toku toonami travel-channel tres tru-tv true-crime-network
tudn tv-k-pop tv-land tvg-2 tvg-network tvw twist tyt ufc-fight-pass ufc unimas
universal-kids-en-espanol universal-kids univision up-tv usa v-me vh1 vice viceland
viendo-movies vme-kids vsin waypoint-tv we-tv weather-channel weathernation wgn-america willow
willow-xtra wnba-league-pass world-fishing-network world-pbs wwe xcorps-tv yes-network
you-too-america z-living
""".split()

# Tablo's abbreviations -> collection names
ALIASES = {
    "catchy": "catchy-comedy", "foxwx": "fox-weather", "foxweather": "fox-weather",
    "365blk": "the-365", "365": "the-365", "hi": "heroes-and-icons", "handi": "heroes-and-icons",
    "heroesicons": "heroes-and-icons", "metv": "me-tv", "metvplus": "me-tv-plus",
    "metvtoons": "me-tv-toons", "cw": "the-cw", "thecw": "the-cw", "mnt": "my-network-tv",
    "mynetworktv": "my-network-tv", "mytv": "my-network-tv", "ion": "ion-television",
    "iontv": "ion-television", "iontelevision": "ion-television", "ionplus": "ion-plus",
    "ionmystery": "ion-mystery", "antennatv": "antenna", "nest": "the-nest", "thenest": "the-nest",
    "truecrime": "true-crime-network", "tcn": "true-crime-network", "courttv": "court-tv",
    "startv": "start-tv", "start": "start-tv", "cozi": "cozi-tv", "cozitv": "cozi-tv",
    "gettv": "get-tv", "lawcrime": "law-and-crime-network", "atlpbs": "pbs", "gpb": "pbs",
    "cbs": "cbs-logo-white", "telemundo": "telemundo", "univision": "univision",
    "unimas": "unimas", "oxygen": "oxygen", "quest": "quest", "create": "create",
}

_INDEX = {}
for _s in _STEMS:
    _INDEX.setdefault(re.sub(r"[^a-z0-9]", "", _s), _s)


def _key(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _lookup(text):
    k = _key(text)
    if not k:
        return None
    stem = ALIASES.get(k) or (k in _INDEX and _INDEX[k]) or _INDEX.get(k + "tv")
    return BASE.format(stem) if stem else None


def find(channel):
    """URL of a backup logo for a channel dict (call_sign, network, minor), or None."""
    for text in (channel.get("call_sign"), channel.get("name")):
        url = _lookup(text)
        if url:
            return url
    if int(channel.get("minor") or 0) <= 1 or channel.get("kind") != "ota":
        return _lookup(channel.get("network"))
    return None


def add(channels, log=lambda m: None):
    """Give channels without a logo a backup one, and add a backup as the last resort for
    channels whose Tablo logos may be missing (Tablo lists some that don't exist)."""
    added = []
    for c in channels:
        url = find(c)
        if not url:
            continue
        logos = list(c.get("logos") or [])
        if url in logos:
            continue
        c["logos"] = logos + [url]
        if not c.get("logo"):
            c["logo"] = url
            added.append(c.get("number") or c.get("call_sign") or "?")
    if added:
        log("backup logos (tv-logos collection) for: " + ", ".join(added))
    return channels
