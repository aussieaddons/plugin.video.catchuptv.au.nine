from brightcove.api import Brightcove
from xbmcswift2 import Plugin, SortMethod
from urllib import urlopen, quote
import json

JUMPIN_WIDGET_CONFIG_URL = 'http://jumpin-widgets.static9.net.au/globalconfig/iphone'
TV_CAT_API_URL = 'http://tv-api-cat.api.jump-in.com.au'

plugin = Plugin()

def load_json(url):
  fp = urlopen(url)
  return json.load(fp)

def filter_drm_shows(show):
  return not show['drm']

def filter_has_episodes(show):
  return show['episodeCount'] > 0

def map_tv_channel(channel):
  if channel == 'Channel 9':
    return 'Nine Network'
  else:
    return channel

def show_data_to_xbmc_dict(show):
  return {
    'label': show['title'],
    'thumbnail': show['image']['showImage'],
    'path': plugin.url_for('show', slug=show['slug']),
    'info': {
      'plot': show['description'],
      'plotoutline': show['description'],
      'tvshowtitle': show['title'],
      'studio': map_tv_channel(show['tvChannel']),
      'genre': show['genre']
    },
    'properties': {
      'fanart_image': show['image']['showImage']
    }
  }

def season_data_to_xbmc_dict(season):
  return {
    'label': season['title'],
    'path': plugin.url_for('season', slug=season['slug'])
  }

def episode_data_to_xbmc_dict(episode):
  return {
    'label': episode['title'],
    'thumbnail': episode['images']['videoStill'],
    'path': plugin.url_for('play', videoId=episode['videoId']),
    'info': {
      'plot': episode['description'],
      'plotoutline': episode['description'],
      'episode': episode['episodeNumber'],
      'genre': episode['genre'],
      'studio': map_tv_channel(episode['tvChannel'])
    },
    'is_playable': True
  }

def get_api_token(type = 'ninemsnCatchup'):
  data = load_json(JUMPIN_WIDGET_CONFIG_URL)
  return data['brightcoveApiTokenLookup'][type]

@plugin.route('/')
def index():
  data = load_json(TV_CAT_API_URL + '/shows?take=-1')
  shows = filter(filter_has_episodes, filter(filter_drm_shows, data['payload']))
  items = map(show_data_to_xbmc_dict, shows)
  plugin.set_content('tvshows')
  return plugin.finish(items, sort_methods=[SortMethod.LABEL_IGNORE_THE])

@plugin.route('/shows/<slug>')
def show(slug):
  data = load_json(TV_CAT_API_URL + '/shows/' + quote(slug, safe='') + '?fields=true')

  items = map(season_data_to_xbmc_dict, data['seasons'])
  plugin.set_content('seasons')
  return plugin.finish(items)

@plugin.route('/seasons/<slug>')
def season(slug):
  data = load_json(TV_CAT_API_URL + '/seasons/' + quote(slug, safe='') + '?fields=true')

  items = map(episode_data_to_xbmc_dict, data['episodes'])

  def add_show_data(item):
    item['info'].update({
      "season": data['title'],
    })
    item['properties'] = {
      'fanart_image': data['show']['image']['showImage']
    }
    return item
  items = map(add_show_data, items)

  plugin.set_content('episodes')
  return plugin.finish(items)

@plugin.route('/play/<videoId>')
def play(videoId):
  api_token = get_api_token()
  brightcove = Brightcove(api_token)
  video = brightcove.find_video_by_id(videoId, media_delivery='http')
  plugin.set_resolved_url(video.videoFullLength['url'])

if __name__ == '__main__':
    plugin.run()
