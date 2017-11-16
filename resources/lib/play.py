import comm
import config
import drmhelper
import os
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


def parse_m3u8(data, m3u8_path, qual=-1, live=False):
    """
    Parse the retrieved m3u8 stream list into a list of dictionaries
    then return the url for the highest quality stream.
    """
    ver = 0
    if '#EXT-X-VERSION:3' in data:
        ver = 3
        data.remove('#EXT-X-VERSION:3')
    if '#EXT-X-VERSION:4' in data:
        ver = 4
        data.remove('#EXT-X-VERSION:4')
    if '#EXT-X-INDEPENDENT-SEGMENTS' in data:
        data.remove('#EXT-X-INDEPENDENT-SEGMENTS')
    count = 1
    m3u_list = []
    while count < len(data):
        if ver == 3 or ver == 0:
            line = data[count]
            line = line.strip('#EXT-X-STREAM-INF:')
            line = line.strip('PROGRAM-ID=1,')
            if 'CODECS' in line:
                line = line[:line.find('CODECS')]
            if line.endswith(','):
                line = line[:-1]
            line = line.strip()
            line = line.split(',')
            linelist = [i.split('=') for i in line]
            if live:
                url = urlparse.urljoin(m3u8_path, data[count + 1])
            else:
                url = data[count + 1]
            linelist.append(['URL', url])
            m3u_list.append(dict((i[0], i[1]) for i in linelist))
            count += 2

        if ver == 4:
            line = data[count]
            line = line.strip('#EXT-X-STREAM-INF:')
            line = line.strip('PROGRAM-ID=1,')
            values = line.split(',')
            for value in values:
                if value.startswith('BANDWIDTH'):
                    bw = value
                elif value.startswith('RESOLUTION'):
                    res = value
            url = urlparse.urljoin(m3u8_path, data[count + 1])
            m3u_list.append(
                dict([bw.split('='), res.split('='), ['URL', url]]))
            count += 3

    sorted_m3u_list = sorted(m3u_list, key=lambda k: int(k['BANDWIDTH']))
    utils.log('Available streams are: {0}'.format(sorted_m3u_list))
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
            data = urllib2.urlopen(m3u8).read().splitlines()
            qual = int(xbmcaddon.Addon().getSetting('LIVEQUALITY'))
            url = parse_m3u8(data, m3u8_path=m3u8, qual=qual, live=live)
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
