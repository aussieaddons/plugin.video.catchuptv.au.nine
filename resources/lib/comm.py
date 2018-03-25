import classes
import config
import json
import requests

from aussieaddonscommon.exceptions import AussieAddonsException
from aussieaddonscommon import session
from aussieaddonscommon import utils


def fetch_url(url, headers={}):
    """
    Use custom session to grab URL and return the text
    """
    with session.Session(force_tlsv1=True) as sess:
        res = sess.get(url, headers=headers)
        try:
            data = json.loads(res.text)
            return data
        except ValueError as e:
            utils.log('Error parsing JSON, response is {0}'.format(res.text))
            raise e


def fetch_bc_url(url, headers={}):
    """
    Use fetch_url and catch Brightcove API errors
    """
    try:
        data = fetch_url(url=url, headers=headers)
        return data
    except requests.exceptions.HTTPError as e:
        utils.log(e.response.text)
        if e.response.status_code == 403:
            try:
                data = json.loads(e.response.text)
                if data[0].get('error_subcode') == 'CLIENT_GEO':
                    raise AussieAddonsException(
                        'Content is geoblocked, your detected country is: {0}'
                        ''.format(data[0].get('client_geo')))
                else:
                    raise e
            except:
                raise e
        else:
            raise e


def list_series():
    """
    Create and return list of series objects
    """
    data = fetch_url(config.TVSERIES_URL)
    listing = []
    for show in data['items']:
        if show.get('containsSeason'):
            for season in reversed(show['containsSeason']):
                s = classes.series()
                s.multi_season = len(show['containsSeason']) > 1
                s.season_slug = season.get('slug')
                s.series_name = utils.ensure_ascii(show.get('name'))
                s.season_name = utils.ensure_ascii(season.get('name'))
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
    data = fetch_url(config.GENRES_URL)
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
    data = fetch_url(url)
    listing = []
    for section in data['items']:
        # filter extras etc for most shows.
        if section.get('callToAction'):
            if (section['callToAction']['link']['type'] not in
               ['episode-index', 'external']):
                continue
        for episode in section['items']:
            # filter possible blank entries
            if not episode:
                continue
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
            e.desc = utils.ensure_ascii(episode.get('description'))
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
    data = fetch_url(config.LIVETV_URL)
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
