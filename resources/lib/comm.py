import classes
import config
import json

from aussieaddonscommon import session


def fetch_url(url, headers={}):
    """
    Use custom session to grab URL and return the text
    """
    with session.Session(force_tlsv1=True) as sess:
        res = sess.get(url, headers=headers)
        return res.text


def list_series():
    """
    Create and return list of series objects
    """
    res = fetch_url(config.TVSERIES_URL)
    data = json.loads(res)
    listing = []
    for show in data['items']:
        if show.get('containsSeason'):
            for season in reversed(show['containsSeason']):
                s = classes.series()
                s.multi_season = len(show['containsSeason']) > 1
                s.season_slug = season.get('slug')
                s.series_name = show.get('name')
                s.season_name = season.get('name')
                s.series_slug = season['partOfSeries'].get('slug')
                s.fanart = show['image']['sizes'].get('w1280')
                s.thumb = season['image']['sizes'].get('w480')
                s.genre = season['genre'].get('name')
                s.title = s.get_title()
                listing.append(s)
    return listing


def list_genres():
    """
    Create and return list of genre objects
    """
    res = fetch_url(config.GENRES_URL)
    data = json.loads(res)
    listing = []
    for genre in data['items']:
        g = classes.genre()
        g.fanart = genre['image']['sizes'].get('w1280')
        g.thumb = genre['image']['sizes'].get('w480')
        g.genre_slug = genre.get('slug')
        g.title = genre.get('name')
        listing.append(g)
    return listing


def list_episodes(params):
    """
    Create and return list of episode objects
    """
    url = config.EPISODEQUERY_URL.format(
        params['series_slug'], params['season_slug'])
    res = fetch_url(url)
    data = json.loads(res)
    listing = []
    for section in data['items']:
        # filter extras etc for most shows.
        if section.get('callToAction'):
            if (section['callToAction']['link']['type'] not in
               ['episode-index', 'external']):
                continue
        for episode in section['items']:
            # filter extras again as some show are unable to be filtered at the
            # previous step
            if not episode.get('episodeNumber'):
                continue
            # make sure season numbers match, some shows return all seasons.
            if episode['partOfSeason'].get('slug') != params['season_slug']:
                continue

            e = classes.episode()
            e.episode_no = str(episode['episodeNumber'])
            e.thumb = episode['image']['sizes'].get('w480')
            e.fanart = data['tvSeries']['image']['sizes'].get('w1280')
            e.episode_name = episode.get('name').encode('utf8')
            e.title = e.get_title()
            e.desc = episode.get('description')
            e.duration = episode['video'].get('duration')//1000
            e.airdate = episode.get('airDate')
            e.id = episode['video'].get('referenceId')
            e.drm = episode['video'].get('drm')
            listing.append(e)
    return listing


def list_live(params):
    """
    Create and return list of channel objects
    """
    res = fetch_url(config.LIVETV_URL)
    data = json.loads(res)
    listing = []
    for channel in data['channels']:
        c = classes.channel()
        c.title = channel.get('name')
        c.fanart = channel['image']['sizes'].get('w1280')
        c.thumb = channel['image']['sizes'].get('w480')
        c.desc = channel['listings'][0].get('name')
        c.episode_name = channel['listings'][0].get('episodeTitle')
        c.id = channel.get('referenceId')
        listing.append(c)
    return listing


def get_subtitles(text_tracks):
    """ Parse subtitles url from 'text_tracks' JSON"""
    for text_track in text_tracks:
        try:
            sub_url = text_track.get('src')
            if sub_url:
                return sub_url
        except AttributeError:
            pass
    return None


def get_stream(url, live=False):
    """Parse episode/channel JSON and return stream URL and subtitles URL
    """
    res = fetch_url(url, headers={'BCOV-POLICY': config.BRIGHTCOVE_KEY})
    data = json.loads(res)
    stream = {}

    if live:
        stream['url'] = data['sources'][0].get('src')
        return stream

    url = None
    for source in data.get('sources'):
        if (source.get('container') == 'M2TS' or
                source.get('type') == 'application/vnd.apple.mpegurl' or
                source.get('type') == 'application/x-mpegURL'):
            if (source.get('type') == 'application/x-mpegURL' and
                    source.get('ext_x_version') in ['4', '5']):
                        continue
            if 'https' in source.get('src'):
                url = source.get('src')
                if url:
                    stream['url'] = url
                    break

    stream['sub_url'] = get_subtitles(data.get('text_tracks'))

    return stream


def get_widevine_auth(drm_url):
    """
    Parse DRM JSON and return license auth URL, manifest URL, and subtitles URL
    """
    res = fetch_url(drm_url, headers={'BCOV-POLICY': config.BRIGHTCOVE_KEY})
    data = json.loads(res)
    stream = {}
    for source in data['sources']:
        if 'com.widevine.alpha' in source['key_systems']:
            url = source['src']
            key = source['key_systems']['com.widevine.alpha']['license_url']
            stream.update({'url': url, 'key': key})
            break

    stream['sub_url'] = get_subtitles(data.get('text_tracks'))

    return stream
