import csv
import os
import sys
import drmhelper
import StringIO

import urlparse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from aussieaddonscommon import utils
from aussieaddonscommon import session as custom_session

import resources.lib.comm as comm
import resources.lib.config as config

from pycaption import SRTWriter
from pycaption import WebVTTReader


def parse_m3u8(m3u8_url, qual=-1, live=False):
    """
    Parse the retrieved m3u8 stream list into a list of dictionaries
    then return the url for the highest quality stream.
    """
    # most shows have 5 streams of different quality, but some have 6 or more
    # so we'll make sure that the highest quality is chosen if it's set that
    # way in the settings.
    if qual == config.MAX_HLS_QUAL:
        qual = -1

    m3u_list = []
    with custom_session.Session() as s:
        data = s.get(m3u8_url, verify=False).text.splitlines()
    iterable = iter(data)
    for line in iterable:
        prefix = '#EXT-X-STREAM-INF:'
        if line.startswith(prefix):
            buff = StringIO.StringIO(line[len(prefix):])
            for line in csv.reader(buff):
                stream_inf = line
                break
            # hack because csv can't parse commas in quotes if preceded by text
            # 'CODECS="mp4a.40.2,avc1.420015"'
            enum = enumerate(stream_inf)
            for idx, x in enum:
                if x.count('"') == 1:
                    stream_inf[idx] = '{0},{1}'.format(x, stream_inf[idx + 1])
                    stream_inf.pop(idx + 1)
                    next(enum)

            stream_data = dict(map(lambda x: x.split('='), stream_inf))
            if live:
                url = urlparse.urljoin(m3u8_url, iterable.next())
            else:
                url = iterable.next()
            stream_data['URL'] = url
            m3u_list.append(stream_data)

    sorted_m3u_list = sorted(m3u_list, key=lambda k: int(k['BANDWIDTH']))
    utils.log('Available streams are: {0}'.format(sorted_m3u_list))
    utils.log('Quality is: {0}'.format(qual))
    try:
        stream = sorted_m3u_list[qual]['URL']
    except IndexError:  # less streams than we expected - go with highest
        stream = sorted_m3u_list[-1]['URL']
    return stream


def play_video(params):
    """
    Determine content and pass url to Kodi for playback
    """
    try:
        _url = sys.argv[0]
        _handle = int(sys.argv[1])
        json_url = config.BRIGHTCOVE_DRM_URL.format(
            config.BRIGHTCOVE_ACCOUNT, params['id'])

        if params.get('drm') == 'True':
            if xbmcaddon.Addon().getSetting('ignore_drm') == 'false':
                if not drmhelper.check_inputstream():
                    return
            widevine = comm.get_widevine_auth(json_url)
            url = widevine['url']
            sub_url = widevine['sub_url']
            play_item = xbmcgui.ListItem(path=url)
            play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
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
            play_item = xbmcgui.ListItem(path=url)
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
        raise
        utils.handle_error('Unable to play video')
