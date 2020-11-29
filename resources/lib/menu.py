import sys

from future.moves.urllib.parse import quote_plus

from aussieaddonscommon import utils

import resources.lib.comm as comm
import resources.lib.config as config

import xbmcgui

import xbmcplugin


def create_listitem(*args, **kwargs):
    ver = utils.get_kodi_major_version()
    if ver >= 18:
        kwargs['offscreen'] = True

    listitem = xbmcgui.ListItem(*args, **kwargs)
    return listitem


def list_categories():
    """
    Make initial list
    """
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        listing = []
        categories = config.CATEGORIES
        for category in categories:
            li = create_listitem(category)
            url_string = '{0}?action=listcategories&category={1}'
            url = url_string.format(_url, category)
            is_folder = True
            listing.append((url, li, is_folder))

        genres = comm.list_genres()
        for g in genres:
            li = create_listitem(g.title)
            li.setArt({'fanart': g.fanart,
                       'icon': g.thumb,
                       'thumb': g.thumb})
            url_string = '{0}?action=listcategories&category=genre&genre={1}'
            url = url_string.format(_url, quote_plus(g.genre_slug))
            is_folder = True
            listing.append((url, li, is_folder))
        li = create_listitem('Settings')
        listing.append(('{0}?action=settings'.format(_url), li, is_folder))
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list categories')


def make_episodes_list(params):
    """ Make list of episode Listitems for Kodi"""
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        episodes = comm.list_episodes(params)
        listing = []
        for e in episodes:
            li = create_listitem(e.title)
            li.setArt({'fanart': e.fanart,
                       'icon': e.thumb,
                       'thumb': e.thumb})
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


def make_live_list(params):
    """ Make list of channel Listitems for Kodi"""
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        channels = comm.list_live(params)
        listing = []
        for c in channels:
            li = create_listitem(c.title)
            li.setArt({'fanart': c.fanart,
                       'icon': c.thumb,
                       'thumb': c.thumb})
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


def make_series_list(params):
    """ Make list of series Listitems for Kodi"""
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        series_list = comm.list_series()
        if 'genre' in params:
            series_slug_list = comm.list_series_by_genre(params['genre'])
            series_list = [s for s in series_list
                           if s.series_slug in series_slug_list]
        listing = []
        for s in series_list:
            li = create_listitem(s.title)
            li.setArt({'fanart': s.fanart,
                       'icon': s.thumb,
                       'thumb': s.thumb})
            url = '{0}?action=listseries{1}'.format(_url, s.make_kodi_url())
            is_folder = True
            li.setInfo('video', {'plot': s.desc, 'plotoutline': s.desc})
            listing.append((url, li, is_folder))

        xbmcplugin.addSortMethod(
            _handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    except Exception:
        utils.handle_error('Unable to list series')
