import xbmcgui
import xbmcplugin
import comm
import config
import sys
import urlparse
import urllib

from aussieaddonscommon import utils

_url = sys.argv[0]
_handle = int(sys.argv[1])


def list_categories():
    """
    Make initial list
    """
    try:
        listing = []
        categories = config.CATEGORIES
        for category in categories:
            li = xbmcgui.ListItem(category, offscreen=True)
            url_string = '{0}?action=listcategories&category={1}'
            url = url_string.format(_url, category)
            is_folder = True
            listing.append((url, li, is_folder))

        genres = comm.list_genres()
        for g in genres:
            li = xbmcgui.ListItem(g.title, iconImage=g.thumb,
                                  thumbnailImage=g.thumb, offscreen=True)
            li.setArt({'fanart': g.fanart})
            url_string = '{0}?action=listcategories&category=genre&genre={1}'
            url = url_string.format(_url, urllib.quote_plus(g.genre_slug))
            is_folder = True
            listing.append((url, li, is_folder))
        li = xbmcgui.ListItem('Settings', offscreen=True)
        listing.append(('{0}?action=settings'.format(_url), li, is_folder))
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list categories')


def make_episodes_list(url):
    """ Make list of episode Listitems for Kodi"""
    try:
        params = dict(urlparse.parse_qsl(url))
        episodes = comm.list_episodes(params)
        listing = []
        for e in episodes:
            li = xbmcgui.ListItem(e.title, iconImage=e.thumb,
                                  thumbnailImage=e.thumb, offscreen=True)
            li.setArt({'fanart': e.fanart})
            url = '{0}?action=listepisodes{1}'.format(_url, e.make_kodi_url())
            is_folder = False
            li.setProperty('IsPlayable', 'true')
            if e.drm is True:
                li.setProperty('inputstreamaddon', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            li.setInfo('video', {'plot': e.desc,
                                 'plotoutline': e.desc,
                                 'duration': e.duration,
                                 'date': e.airdate})
            listing.append((url, li, is_folder))

        xbmcplugin.addSortMethod(
            _handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(
            _handle, xbmcplugin.SORT_METHOD_EPISODE)
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list episodes')


def make_live_list(url):
    """ Make list of channel Listitems for Kodi"""
    try:
        params = dict(urlparse.parse_qsl(url))
        channels = comm.list_live(params)
        listing = []
        for c in channels:
            li = xbmcgui.ListItem(c.title, iconImage=c.thumb,
                                  thumbnailImage=c.thumb, offscreen=True)
            li.setArt({'fanart': c.fanart})
            url = '{0}?action=listchannels{1}'.format(_url, c.make_kodi_url())
            is_folder = False
            li.setProperty('IsPlayable', 'true')
            li.setInfo('video', {'plot': c.desc,
                                 'plotoutline': c.episode_name})
            listing.append((url, li, is_folder))

        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list channels')


def make_series_list(url):
    """ Make list of series Listitems for Kodi"""
    try:
        params = dict(urlparse.parse_qsl(url))
        series_list = comm.list_series()
        if 'genre' in params:
            series_slug_list = comm.list_series_by_genre(params['genre'])
            series_list = [s for s in series_list
                            if s.series_slug in series_slug_list]
        listing = []
        for s in series_list:
            li = xbmcgui.ListItem(s.title, iconImage=s.thumb,
                                  thumbnailImage=s.thumb, offscreen=True)
            li.setArt({'fanart': s.fanart})
            url = '{0}?action=listseries{1}'.format(_url, s.make_kodi_url())
            is_folder = True
            listing.append((url, li, is_folder))

        xbmcplugin.addSortMethod(
            _handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list series')
