import xbmcgui
import xbmcaddon
import xbmcplugin
import comm
import config
import sys
import urllib2
import urlparse
import drmhelper

from aussieaddonscommon import utils

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
            m3u8 = comm.get_stream(json_url, live=live)
            data = urllib2.urlopen(m3u8).read().splitlines()
            qual = int(xbmcaddon.Addon().getSetting('LIVEQUALITY'))
            url = parse_m3u8(data, m3u8_path=m3u8, qual=qual, live=live)
            play_item = xbmcgui.ListItem(path=url)
        
        xbmcplugin.setResolvedUrl(_handle, True, play_item)
    except Exception:
        utils.handle_error('Unable to play video')
