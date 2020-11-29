import json

import requests

from aussieaddonscommon import utils
from aussieaddonscommon.exceptions import AussieAddonsException

import resources.lib.classes as classes
import resources.lib.config as config

cache = classes.CacheObj()
ADDON_ID = 'plugin.video.catchuptv.au.nine'


def fetch_bc_url(url, headers={}):
    """
    Use fetch_url and catch Brightcove API errors
    """
    try:
        data = cache.getData(url=url, headers=headers, noCache=True)
        return data
    except requests.exceptions.HTTPError as e:
        utils.log(e.response.text)
        if e.response.status_code == 403:
            try:
                error_data = json.loads(e.response.text)
                if error_data[0].get('error_subcode') == 'CLIENT_GEO':
                    raise AussieAddonsException(
                        'Content is geoblocked, your detected country is: {0}'
                        ''.format(error_data[0].get('client_geo')))
                else:
                    raise e
            except IndexError:
                raise e
            except ValueError:
                raise
        else:
            raise e


def list_series():
    """
    Create and return list of series objects
    """
    data = cache.getData(name=ADDON_ID, url=config.TVSERIES_URL)

    if isinstance(data, list):
        return data

    listing = []
    for show in data['items']:
        if show.get('containsSeason'):
            for season in reversed(show['containsSeason']):
                s = classes.Series()
                s.multi_season = len(show['containsSeason']) > 1
                s.season_slug = season.get('slug')
                s.series_name = utils.ensure_ascii(show.get('name'))
                s.season_name = utils.ensure_ascii(season.get('name'))
                s.series_slug = season['partOfSeries'].get('slug')
                s.fanart = show['image']['sizes'].get('w1280')
                s.thumb = season['image']['sizes'].get('w480')
                s.genre = season['genre'].get('name')
                s.genre_slug = season['genre'].get('slug')
                s.title = s.get_title()
                s.desc = season.get('description')
                listing.append(s)

    cache.getData(name=ADDON_ID, url=config.TVSERIES_URL, data=listing)
    return listing


def list_series_by_genre(genre):
    """
    Create and return list of series objects
    """
    url = config.TVSERIESQUERY_URL.format(genre)
    data = cache.getData(name=ADDON_ID, url=url)

    if isinstance(data, list):
        return data

    data = data.get('tvSeries', None)
    listing = [s['slug'] for s in data] if data else []

    cache.getData(name=ADDON_ID, url=url, data=listing)
    return listing


def list_genres():
    """
    Create and return list of genre objects
    """
    data = cache.getData(name=ADDON_ID, url=config.GENRES_URL)

    if isinstance(data, list):
        return data

    listing = []
    for genre in data['items']:
        g = classes.Genre()
        g.fanart = genre['image']['sizes'].get('w1280')
        g.thumb = genre['image']['sizes'].get('w480')
        g.genre_slug = genre.get('slug')
        g.title = genre.get('name')
        listing.append(g)

    cache.getData(name=ADDON_ID, url=config.GENRES_URL, data=listing)
    return listing


def list_episodes(params):
    """
    Create and return list of episode objects
    """
    def get_metadata(episode):
        if not episode:
            return
        # filter extras again as some show are unable to be filtered at the
        # previous step
        if not episode.get('episodeNumber'):
            return
        # make sure season numbers match, some shows return all seasons.
        if ('partOfSeason' in episode and
                episode['partOfSeason'].get('slug') != params['season_slug']):
            return

        e = classes.Episode()
        e.episode_no = str(episode['episodeNumber'])
        e.thumb = episode['image']['sizes'].get('w480')
        e.fanart = data['tvSeries']['image']['sizes'].get('w1280')
        e.episode_name = episode.get('name').encode('utf8')
        e.title = e.get_title()
        e.desc = utils.ensure_ascii(episode.get('description'))
        e.duration = episode['video'].get('duration')//1000
        airdate = episode.get('airDate')
        if airdate:
            e.airdate = '{0}.{1}.{2}'.format(airdate[8:10],
                                             airdate[5:7],
                                             airdate[0:4])
        e.id = episode['video'].get('referenceId')
        e.drm = episode['video'].get('drm')
        e.series_slug = params['series_slug']
        e.series_title = data['tvSeries']['name']
        e.season_slug = params['season_slug']
        e.season_no = str(data['season']['seasonNumber'])
        return e

    url = config.EPISODEQUERY_URL.format(params['series_slug'],
                                         params['season_slug'],
                                         params.get('episode_slug', ''))
    data = cache.getData(name=ADDON_ID, url=url)

    if isinstance(data, list):
        if params.get('episode'):
            return [e for e in data
                    if e.episode_no == str(params.get('episode'))]
        return data

    episodes = []
    if 'episode' in data:
        episodes = [data['episode']]
    elif 'episodes' in data:
        episodes = data['episodes'].get('items')
    elif 'items' in data:
        episodes = data['items']

    listing = []
    for episode in episodes:
        e = get_metadata(episode)
        if e:
            listing.append(e)

    cache.getData(name=ADDON_ID, url=url, data=listing)
    if params.get('episode'):
        return [x for x in listing
                if x.episode_no == str(params.get('episode'))]
    return listing


def get_next_episode(episode):
    if not episode:
        return None

    params = dict(series_slug=episode['series_slug'],
                  season_slug=episode['season_slug'],
                  episode=int(episode['episode_no'])+1)

    episodes = list_episodes(params)
    return episodes[0] if episodes else None


def list_live(params):
    """
    Create and return list of channel objects
    """
    data = cache.getData(name=ADDON_ID, url=config.LIVETV_URL)

    if isinstance(data, list):
        return data

    listing = []
    for channel in data['channels']:
        c = classes.Channel()
        c.title = channel.get('name')
        c.fanart = channel['image']['sizes'].get('w1280')
        c.thumb = channel['image']['sizes'].get('w480')
        c.desc = channel['listings'][0].get('name')
        c.episode_name = channel['listings'][0].get('episodeTitle')
        c.id = channel.get('referenceId')
        listing.append(c)
    for channel in data['events']:
        c = classes.Channel()
        c.title = channel.get('name')
        c.fanart = channel['image']['sizes'].get('w1280')
        c.thumb = channel['image']['sizes'].get('w480')
        c.desc = channel.get('description')
        c.episode_name = channel.get('name')
        c.id = channel.get('referenceId')
        listing.append(c)

    cache.getData(name=ADDON_ID, url=config.LIVETV_URL, data=listing)
    return listing


def get_subtitles(text_tracks):
    """ Parse subtitles url from 'text_tracks' JSON"""
    for text_track in text_tracks:
        try:
            sub_url = text_track.get('src')
            label = text_track.get('label')
            if sub_url and label != 'thumbnails':
                return sub_url
        except AttributeError:
            pass
    return None


def get_stream(url, live=False):
    """Parse episode/channel JSON and return stream URL and subtitles URL
    """
    data = fetch_bc_url(url, headers={'BCOV-POLICY': config.BRIGHTCOVE_KEY})
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
    data = fetch_bc_url(drm_url,
                        headers={'BCOV-POLICY': config.BRIGHTCOVE_KEY})
    stream = {}
    for source in data['sources']:
        if 'com.widevine.alpha' in source['key_systems']:
            url = source['src']
            key = source['key_systems']['com.widevine.alpha']['license_url']
            stream.update({'url': url, 'key': key})
            break

    stream['sub_url'] = get_subtitles(data.get('text_tracks'))

    return stream
