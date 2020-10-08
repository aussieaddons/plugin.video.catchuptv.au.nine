import urlparse
import urllib
import unicodedata
import json
import datetime
import xbmcgui

from config import USER_AGENT

from threading import Thread
from collections import deque

from aussieaddonscommon import session
from aussieaddonscommon import utils


class genre(object):
    def __init__(self, attrs=None):
        if attrs:
            for attr, val in attrs.items():
                setattr(self, attr, val)
            return

        self.fanart = None
        self.thumb = None
        self.title = None
        self.genre_slug = None

    def __repr__(self):
        return type(self).__name__ + '(' + str(dict(vars(self).items())) + ')'

    def make_kodi_url(self):
        d = vars(self)
        for key, value in d.iteritems():
            if isinstance(value, unicode):
                d[key] = unicodedata.normalize(
                    'NFKD', value).encode('ascii', 'ignore')
        return '&{0}'.format(urllib.urlencode(d))

    def parse_kodi_url(self, url):
        params = urlparse.parse_qsl(url)
        for item in params.keys():
            setattr(self, item, urllib.unquote_plus(params[item]))


class series(object):
    def __init__(self, attrs=None):
        if attrs:
            for attr, val in attrs.items():
                setattr(self, attr, val)
            return

        self.multi_season = None
        self.fanart = None
        self.thumb = None
        self.series_name = None
        self.series_slug = None
        self.season_name = None
        self.season_slug = None
        self.title = None
        self.genre = None
        self.genre_slug = None
        self.desc = None

    def __repr__(self):
        return type(self).__name__ + '(' + str(dict(vars(self).items())) + ')'

    def get_title(self):
        if self.multi_season:
            return '{0} {1}'.format(self.series_name, self.season_name)
        else:
            return self.series_name

    def make_kodi_url(self):
        d = vars(self)
        for key in d.keys():
            if not d[key]:
                d.pop(key)
                continue
            if isinstance(d[key], unicode):
                d[key] = unicodedata.normalize(
                    'NFKD', d[key]).encode('ascii', 'ignore')
        return '&{0}'.format(urllib.urlencode(d))

    def parse_kodi_url(self, url):
        params = dict(urlparse.parse_qsl(url))
        for item in params.keys():
            setattr(self, item, urllib.unquote_plus(params[item]))


class episode(object):
    def __init__(self, attrs=None):
        if attrs:
            for attr, val in attrs.items():
                setattr(self, attr, val)
            return

        self.series_slug = None
        self.series_title = None
        self.season_slug = None
        self.season_no = None
        self.fanart = None
        self.thumb = None
        self.title = None
        self.desc = None
        self.duration = None
        self.airdate = None
        self.episode_no = None
        self.episode_name = None
        self.url = None
        self.id = None
        self.drm = None
        self.license_url = None
        self.license_key = None

    def __repr__(self):
        return type(self).__name__ + '(' + str(dict(vars(self).items())) + ')'

    def get_title(self):
        return 'Ep {0} - {1}'.format(self.episode_no, self.episode_name)

    def make_kodi_url(self):
        d = vars(self)
        for key, value in d.iteritems():
            if isinstance(value, unicode):
                d[key] = unicodedata.normalize(
                    'NFKD', value).encode('ascii', 'ignore')
        return '&{0}'.format(urllib.urlencode(d))

    def parse_kodi_url(self, url):
        params = urlparse.parse_qsl(url)
        for item in params.keys():
            setattr(self, item, urllib.unquote_plus(params[item]))


class channel(object):
    def __init__(self, attrs=None):
        if attrs:
            for attr, val in attrs.items():
                setattr(self, attr, val)
            return

        self.fanart = None
        self.thumb = None
        self.title = None
        self.desc = None
        self.episode_name = None
        self.url = None
        self.id = None
        self.drm = None

    def __repr__(self):
        return type(self).__name__ + '(' + str(dict(vars(self).items())) + ')'

    def get_title(self):
        return '{0} - {1}'.format(self.title, self.desc)

    def make_kodi_url(self):
        d = vars(self)
        for key, value in d.iteritems():
            if isinstance(value, unicode):
                d[key] = unicodedata.normalize(
                    'NFKD', value).encode('ascii', 'ignore')
        return '&{0}'.format(urllib.urlencode(d))

    def parse_kodi_url(self, url):
        params = urlparse.parse_qsl(url)
        for item in params.keys():
            setattr(self, item, urllib.unquote_plus(params[item]))


class CacheObj():

    maxEntries = 50
    maxTTL = datetime.timedelta(seconds=(60*60*12))
    minTTL = datetime.timedelta(seconds=(60*5))

    def __init__(self):
        self.win = xbmcgui.Window(10000)

    def getData(self, url, headers={},
                name=None, noCache=False, expiry=None, data=None):

        now = datetime.datetime.now()

        if not headers or not headers.get('User-Agent'):
            headers['User-Agent'] = USER_AGENT

        if noCache or not name:
            data = CacheObj.fetch_url(url=url, headers=headers)
        if not name:
            return data

        if not data:
            rawData = self.win.getProperty('%s|%s' % (name, url))
            if rawData:
                try:
                    cachedData = eval(rawData)
                    if not isinstance(expiry, datetime.timedelta):
                        expiry = CacheObj.maxTTL
                    if cachedData[0] + CacheObj.minTTL < now:
                        bgFetch = Thread(target=self.getData,
                                         kwargs=dict(url=url,
                                                     headers=headers,
                                                     name=name,
                                                     noCache=True))
                        bgFetch.start()
                    if cachedData[0] + expiry > now:
                        return cachedData[1]
                except Exception as e:
                    utils.log('Error with eval of cached data: {0}'.format(e))
                    #utils.log(rawData)

            data = CacheObj.fetch_url(url=url, headers=headers)

        cachedData = (now, data)
        self.win.setProperty('%s|%s' % (name, url), repr(cachedData))

        rawURLs = self.win.getProperty('%s|urls' % name)
        urls = eval(rawURLs) if rawURLs else deque()

        if url in urls:
            urls.remove(url)
        urls.append(url)

        if len(urls) > CacheObj.maxEntries:
            oldUrl = urls.popleft()
            self.win.clearProperty('%s|%s' % (name, oldUrl))

        self.win.setProperty('%s|urls' % name, repr(urls))

        return cachedData[1]

    @staticmethod
    def fetch_url(url, headers={}):
        """
        Use custom session to grab URL and return the text
        """
        with session.Session(force_tlsv1=True) as sess:
            res = sess.get(url, headers=headers)
            try:
                data = json.loads(res.text)
                return data
            except ValueError as e:
                utils.log('Error parsing JSON, response is {0}'
                            .format(res.text))
                raise e
