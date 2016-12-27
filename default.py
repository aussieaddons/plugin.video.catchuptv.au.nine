from xbmcswift2 import ListItem, Plugin, SortMethod, xbmcplugin
from ssl import SSLError
import requests

TV_API_BASE = 'https://tv-api.9now.com.au/v2/'
BRIGHTCOVE_API_BASE = 'https://edge.api.brightcove.com/'
BRIGHTCOVE_ACCOUNT_ID = '4460760524001'
BRIGHTCOVE_PLATFORM_KEY = 'BCpkADawqM3lGJpOQdDMZC6_R_ZDm6VxNew-gdLyufvOnkWKzRlAbnX4g3Qu6zzi-esryjIYTrB1km-4qQpfqWel0KiuNtzG_q-vtTHGlu70L7SyEHTkLGNCzSUW6_dZNuE5L92GsjU7W-Uo'

plugin = Plugin()

def load_api(endpoint):
  from requests.packages.urllib3.util.ssl_ import HAS_SNI
  verify = HAS_SNI
  if not verify:
    plugin.log.warning("!!! DISABLING SSL VERIFICATION AS YOUR VERSION OF XBMC DOES NOT SUPPORT SNI !!!")
  r = requests.get(TV_API_BASE + endpoint, params={'device': 'xbmc'}, verify=verify)
  r.raise_for_status()
  return r.json()

def load_brightcove_data(referenceId):
  headers = { 'Accept': 'application/json;pk=' + BRIGHTCOVE_PLATFORM_KEY }
  r = requests.get(BRIGHTCOVE_API_BASE + 'playback/v1/accounts/' + BRIGHTCOVE_ACCOUNT_ID + '/videos/ref:' + referenceId, headers=headers)
  r.raise_for_status()
  return r.json()

def get_largest_image(image):
  sizes = map(lambda size: int(size[1::]), image['sizes'])
  sizes.sort()
  return image['sizes']['w' + str(sizes[-1])]

def all_shows_dict():
  return {
    'label': 'All TV Shows',
    'path': plugin.url_for('all_shows')
  }

def live_tv_dict():
  return {
    'label': 'Live TV',
    'path': plugin.url_for('live_streams')
  }

def genre_data_to_xbmc_dict(genre):
  image = get_largest_image(genre['image'])
  return {
    'label': genre['name'],
    'thumbnail': image,
    'path': plugin.url_for('genre', genre=genre['slug']),
    'properties': {
      'fanart_image': image
    }
  }

@plugin.route('/')
def index():
  data = load_api('/pages/genres')
  items = [ all_shows_dict(), live_tv_dict() ] + map(genre_data_to_xbmc_dict, data['genres'])
  return plugin.finish(items)

def channel_data_to_xbmc_dict(region):
  def listing_description(listings):
    # TODO: include times
    description = "Now: " + listings[0]['name']
    if listings[0]['episodeTitle'] is not None:
      description += ": " + listings[0]['episodeTitle']

    description += "\nNext: " + listings[1]['name']
    if listings[1]['episodeTitle'] is not None:
      description += ": " + listings[1]['episodeTitle']

    return description
  return lambda channel: {
    'label': "%s %s" % (channel['name'], region['name']),
    'thumbnail': get_largest_image(channel['image']),
    'path': plugin.url_for('play_video', referenceId=channel['referenceId']),
    'is_playable': True,
    'info': {
      'plot': listing_description(channel['listings']),
      'plotoutline': listing_description(channel['listings'])
    }
  }

@plugin.route('/live')
def live_streams():
  data = load_api('/pages/livestreams')
  items = map(channel_data_to_xbmc_dict(data['region']), data['channels'])
  plugin.set_content('tvshows')
  return plugin.finish(items)

def tv_series_data_to_xbmc_dict(series):
  image = get_largest_image(series['image'])
  return {
    'label': series['name'],
    'thumbnail': image,
    'path': plugin.url_for('show', series=series['slug']),
    'info': {
      'plot': series['description'],
      'plotoutline': series['description'],
      'tvshowtitle': series['name']
    },
    'properties': {
      'fanart_image': image
    }
  }

@plugin.route('/shows')
def all_shows():
  data = load_api('/pages/tv-series')
  items = map(tv_series_data_to_xbmc_dict, data['tvSeries'])
  plugin.set_content('tvshows')
  return plugin.finish(items, sort_methods=[SortMethod.LABEL_IGNORE_THE])

@plugin.route('/genre/<genre>')
def genre(genre):
  data = load_api('pages/genres/' + genre)
  items = map(tv_series_data_to_xbmc_dict, data['tvSeries'])
  plugin.set_content('tvshows')
  return plugin.finish(items, sort_methods=[SortMethod.LABEL_IGNORE_THE])

def season_data_to_xbmc_dict(series):
  image = get_largest_image(series['image'])
  return lambda season: {
    'label': season['name'],
    'thumbnail': image,
    'path': plugin.url_for('season', series=series['slug'], season=season['slug']),
    'info': {
      'plot': series['description'],
      'plotoutline': series['description'],
      'tvshowtitle': series['name']
    },
    'properties': {
      'fanart_image': image
    }
  }

@plugin.route('/shows/<series>')
def show(series):
  data = load_api('pages/tv-series/' + series)
  items = map(season_data_to_xbmc_dict(data['tvSeries']), data['seasons'])
  plugin.set_content('seasons')
  return plugin.finish(items)

def episode_data_to_xbmc_dict(series, season):
  season_image = get_largest_image(season['image'])

  def episode_data_to_xbmc_dict_inner(episode):
    label = episode['displayName']
    if episode['video']['drm']:
      label += ' [DRM/UNPLAYABLE]'
    return {
      'label': label,
      'thumbnail': get_largest_image(episode['image']),
      'path': episode['video']['brightcoveOnce']['onceUrl'],
      'is_playable': True,
      'info': {
        'plot': episode['description'],
        'plotoutline': episode['description'],
        'tvshowtitle': series['name'],
        'episode': episode['episodeNumber'],
        'season': season['name'],
        'genre': episode['genre']['name']
      },
      'properties': {
        'fanart_image': season_image
      }
    }
  return episode_data_to_xbmc_dict_inner

@plugin.route('/shows/<series>/seasons/<season>')
def season(series, season):
  data = load_api('pages/tv-series/' + series + '/seasons/' + season + '/episodes')
  items = map(episode_data_to_xbmc_dict(data['tvSeries'], data['season']), data['episodes']['items'])
  plugin.set_content('episodes')
  return plugin.finish(items)

@plugin.route('/play/<referenceId>')
def play_video(referenceId):
  data = load_brightcove_data(referenceId)
  path = data['sources'][0]['src']
  return plugin.set_resolved_url(path)


if __name__ == '__main__':
    plugin.run()
