import os
import sys

from aussieaddonscommon import session as custom_session
from aussieaddonscommon import utils

import drmhelper

from pycaption import SRTWriter
from pycaption import WebVTTReader

import resources.lib.comm as comm
import resources.lib.config as config

import xbmc

import xbmcaddon

import xbmcgui

import xbmcplugin


def play_video(params):
    """
    Determine content and pass url to Kodi for playback
    """
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        json_url = config.BRIGHTCOVE_DRM_URL.format(
            config.BRIGHTCOVE_ACCOUNT, params['id'])
        play_item = xbmcgui.ListItem()
        play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        play_item.setProperty('inputstream', 'inputstream.adaptive')

        if params.get('drm') == 'True':
            if xbmcaddon.Addon().getSetting('ignore_drm') == 'false':
                if not drmhelper.check_inputstream():
                    return
            widevine = comm.get_widevine_auth(json_url)
            url = widevine['url']
            sub_url = widevine['sub_url']
            play_item = xbmcgui.ListItem(path=url)
            play_item.setPath(url)
            play_item.setProperty('inputstream.adaptive.manifest_type',
                                  'mpd')
            play_item.setProperty('inputstream.adaptive.license_type',
                                  'com.widevine.alpha')
            play_item.setProperty(
                'inputstream.adaptive.license_key',
                widevine['key'] + ('|Content-Type=application%2F'
                                   'x-www-form-urlencoded|A{SSM}|'))
        else:
            live = params['action'] == 'listchannels'
            stream_data = comm.get_stream(json_url, live=live)
            url = str(stream_data.get('url'))
            sub_url = stream_data.get('sub_url')
            play_item.setPath(url)
            play_item.setProperty('inputstream.adaptive.manifest_type',
                                  'hls')
            utils.log('Playing {0} - {1}'.format(params.get('title'), url))

        if sub_url:
            try:
                utils.log("Enabling subtitles: {0}".format(sub_url))
                profile = xbmcaddon.Addon().getAddonInfo('profile')
                subfilename = xbmc.translatePath(
                    os.path.join(profile, 'subtitle.srt'))
                profiledir = xbmc.translatePath(os.path.join(profile))
                if not os.path.isdir(profiledir):
                    os.makedirs(profiledir)

                with custom_session.Session() as s:
                    webvtt_data = s.get(sub_url).text
                if webvtt_data:
                    with open(subfilename, 'w') as f:
                        webvtt_subtitle = WebVTTReader().read(webvtt_data)
                        srt_subtitle = SRTWriter().write(webvtt_subtitle)
                        srt_unicode = srt_subtitle.encode('utf-8')
                        f.write(srt_unicode)

                if hasattr(play_item, 'setSubtitles'):
                    # This function only supported from Kodi v14+
                    play_item.setSubtitles([subfilename])

            except Exception as e:
                utils.log('Unable to add subtitles: {0}'.format(e))

        play_item.setProperty('isPlayable', 'true')
        if hasattr(play_item, 'setIsFolder'):
            play_item.setIsFolder(False)
        # TODO: add more info
        play_item.setInfo('video', {
            'mediatype': 'episode',
            'tvshowtitle': params.get('series_title', ''),
            'title': params.get('episode_name', ''),
            'plot': params.get('desc', ''),
            'plotoutline': params.get('desc', ''),
            'duration': params.get('duration', ''),
            'aired': params.get('airdate', ''),
            'season': params.get('season_no', ''),
            'episode': params.get('episode_no', '')
        })

        xbmcplugin.setResolvedUrl(_handle, True, play_item)

        if params['action'] != 'listepisodes':
            return
        next_item = comm.get_next_episode(params)
        if not next_item:
            return

        try:
            import upnext
        except Exception as e:
            utils.log('UpNext addon not installed: %s' % e)
            return

        upnext_info = dict(
            current_episode=dict(
                episodeid=params['id'],
                tvshowid=params['series_slug'],
                title=params['episode_name'],
                art={
                    'thumb': params['thumb'],
                    'tvshow.fanart': params['fanart'],
                },
                season=params['season_no'],
                episode=params['episode_no'],
                showtitle=params['series_title'],
                plot=params['desc'],
                playcount=0,
                rating=None,
                firstaired=params['airdate'],
                runtime=params['duration'],
            ),
            next_episode=dict(
                episodeid=next_item.id,
                tvshowid=next_item.series_slug,
                title=next_item.episode_name,
                art={
                    'thumb': next_item.thumb,
                    'tvshow.fanart': next_item.fanart,
                },
                season=next_item.season_no,
                episode=next_item.episode_no,
                showtitle=next_item.series_title,
                plot=next_item.desc,
                playcount=0,
                rating=None,
                firstaired=next_item.airdate,
                runtime=next_item.duration,
            ),
            play_url='{0}?action=listepisodes{1}'.format(
                _url, next_item.make_kodi_url())
        )

        upnext.send_signal(xbmcaddon.Addon().getAddonInfo('id'), upnext_info)

    except Exception:
        utils.handle_error('Unable to play video')
