from xbmcswift2 import Plugin, SortMethod
from urllib import urlopen, quote
import xbmcaddon
import json

TV_CAT_API_URL = 'https://tv-api.9now.com.au/v2/pages/tv-series'

plugin = Plugin()
addon = xbmcaddon.Addon('plugin.video.catchuptv.au.nine')

def load_json(url):
  fp = urlopen(url)
  return json.load(fp)
  
def map_tv_channel(channel):
  if channel == 'Channel 9':
    return 'Nine Network'
  else:
    return channel

def show_data_to_xbmc_dict(show):
  return {
    'label': show['name'],
    'thumbnail': show['image']['sizes']['w320'],
    'path': plugin.url_for('show', slug=show['slug']),
    'info': {
      'plot': show['description'],
      'plotoutline': show['description'],
      'tvshowtitle': show['name'],
    },
    'properties': {
      'fanart_image': show['image']['sizes']['w768']
    }
  }
  
def episode_data_to_xbmc_dict(episode):
  return {
    'label': episode['name'],
    'thumbnail': episode['image']['sizes']['w320'],
    'path': plugin.url_for('play', videoId=episode['video']['brightcoveOnce']['onceUrl']),
    'info': {
      'plot': episode['description'],
      'plotoutline': episode['description'],
      'episode': episode['episodeNumber'],
      'genre': episode['genre']['name'],
	  'aired': episode['airDate']
    },
    'is_playable': True
  }

@plugin.route('/')
def index():
  data = load_json(TV_CAT_API_URL + '?device=web')
  shows = data['tvSeries']
  items = map(show_data_to_xbmc_dict, shows)
  plugin.set_content('tvshows')
  return plugin.finish(items, sort_methods=[SortMethod.LABEL_IGNORE_THE])

@plugin.route('/shows/<slug>')
def show(slug):
  data = load_json(TV_CAT_API_URL + '/' + quote(slug, safe='') + '?device=web')
  items = []
  for season in data['seasons']:
    items.extend([{
	'label': season['name'],
	'path': plugin.url_for('season', show= data['tvSeries']['slug'], slug=season['slug'])
    }])
  
  plugin.set_content('seasons')
  return plugin.finish(items)

@plugin.route('/seasons/<show>/<slug>')
def season(show, slug):
  data = load_json(TV_CAT_API_URL + '/' + quote(show, safe='') + '/seasons/' + quote(slug, safe='')+ '/episodes?device=web')
  items = map(episode_data_to_xbmc_dict, data['episodes']['items'])

  def add_show_data(item):
    item['info'].update({
      "season": data['season']['name'],
    })
    item['properties'] = {
      'fanart_image': data['season']['image']['sizes']['w768']
    }
    return item
  items = map(add_show_data, items)

  plugin.set_content('episodes')
  return plugin.finish(items)

@plugin.route('/play/<videoId>')
def play(videoId):
  plugin.set_resolved_url(videoId)
    
if __name__ == '__main__':
    plugin.run()
	