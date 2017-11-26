import comm
import config
import csv
import drmhelper
import os
import StringIO
import sys
import urllib2
import urlparse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from aussieaddonscommon import utils

from pycaption import SRTWriter
from pycaption import WebVTTReader

_url = sys.argv[0]
_handle = int(sys.argv[1])


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
    data = urllib2.urlopen(m3u8_url).read().splitlines()
    iterable = iter(data)
    for line in iterable:
        if line.startswith('#EXT-X-STREAM-INF:'):
            buff = StringIO.StringIO(line)
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
        if params['drm'] == 'True':
            if xbmcaddon.Addon().getSetting('ignore_drm') == 'false':
                if not drmhelper.check_inputstream():
                    return
            acc = config.BRIGHTCOVE_ACCOUNT
            drm_url = config.BRIGHTCOVE_DRM_URL.format(acc, params['id'])
            widevine = comm.get_widevine_auth(drm_url)
            url = widevine['url']
            sub_url = widevine['sub_url']
            play_item = xbmcgui.ListItem(path=url)
            play_item.setProperty('inputstream.adaptive.manifest_type',
                                  'mpd')
            play_item.setProperty('inputstream.adaptive.license_type',
                                  'com.widevine.alpha')
            play_item.setProperty(
                'inputstream.adaptive.license_key',
                widevine['key']+('|Content-Type=application%2F'
                                 'x-www-form-urlencoded|A{SSM}|'))
        else:
            if params['action'] == 'listchannels':
                qual = int(xbmcaddon.Addon().getSetting('LIVEQUALITY'))
                live = True
            else:
                qual = int(xbmcaddon.Addon().getSetting('HLSQUALITY'))
                live = False

            json_url = config.BRIGHTCOVE_DRM_URL.format(
                config.BRIGHTCOVE_ACCOUNT, params['id'])
            stream_data = comm.get_stream(json_url, live=live)
            m3u8 = stream_data.get('url')
            sub_url = stream_data.get('sub_url')
            url = parse_m3u8(m3u8, qual=qual, live=live)
            play_item = xbmcgui.ListItem(path=url)

        if sub_url:
            try:
                utils.log("Enabling subtitles: {0}".format(sub_url))
                profile = xbmcaddon.Addon().getAddonInfo('profile')
                subfilename = xbmc.translatePath(
                    os.path.join(profile, 'subtitle.srt'))
                profiledir = xbmc.translatePath(os.path.join(profile))
                if not os.path.isdir(profiledir):
                    os.makedirs(profiledir)

                webvtt_data = urllib2.urlopen(
                    sub_url).read().decode('utf-8')
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

        xbmcplugin.setResolvedUrl(_handle, True, play_item)

    except Exception:
        utils.handle_error('Unable to play video')
