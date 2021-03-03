import datetime
import json
import unicodedata
from builtins import str
from collections import OrderedDict, deque
from threading import Thread

from future.backports.urllib.parse import parse_qsl, quote_plus, unquote_plus

from aussieaddonscommon import session
from aussieaddonscommon import utils

from resources.lib.config import USER_AGENT

import xbmcgui


class BaseItem(object):
    def __init__(self, **kwargs):
        self.fanart = None
        self.thumb = None
        self.title = None
        if kwargs:
            for attr, val in kwargs.items():
                setattr(self, attr, val)

    def __repr__(self):
        return type(
            self).__name__ + '(**' + str(dict(vars(self).items())) + ')'

    def make_kodi_url(self):
        d_original = OrderedDict(
            sorted(self.__dict__.items(), key=lambda x: x[0]))
        d = d_original.copy()
        for key, value in d_original.items():
            if not value:
                d.pop(key)
                continue
            if isinstance(value, str):
                d[key] = unicodedata.normalize(
                    'NFKD', value).encode('ascii', 'ignore').decode('utf-8')
        url = ''
        for key in d.keys():
            if isinstance(d[key], (str, bytes)):
                val = quote_plus(d[key])
            else:
                val = d[key]
            url += '&{0}={1}'.format(key, val)
        url += '&addon_version={0}'.format(utils.get_addon_version())
        return url

    def parse_kodi_url(self, url):
        params = dict(parse_qsl(url))
        params.pop('addon_version', '')
        for item in params.keys():
            setattr(self, item, unquote_plus(params[item]))


class Genre(BaseItem):
    def __init__(self, **kwargs):
        self.genre_slug = None
        super(Genre, self).__init__(**kwargs)


class Series(BaseItem):
    def __init__(self, **kwargs):
        self.multi_season = None
        self.series_name = None
        self.series_slug = None
        self.season_name = None
        self.season_slug = None
        self.genre = None
        self.genre_slug = None
        self.desc = None
        super(Series, self).__init__(**kwargs)

    def get_title(self):
        if self.multi_season:
            return '{0} {1}'.format(self.series_name, self.season_name)
        else:
            return self.series_name


class Episode(BaseItem):
    def __init__(self, **kwargs):
        self.series_slug = None
        self.series_title = None
        self.season_slug = None
        self.season_no = None
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
        super(Episode, self).__init__(**kwargs)

    def get_title(self):
        return 'Ep {0} - {1}'.format(self.episode_no, self.episode_name)


class Channel(BaseItem):
    def __init__(self, **kwargs):
        self.desc = None
        self.episode_name = None
        self.url = None
        self.id = None
        self.drm = None
        super(Channel, self).__init__(**kwargs)

    def get_title(self):
        return '{0} - {1}'.format(self.title, self.desc)


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
        with session.Session(force_tlsv1=False) as sess:
            res = sess.get(url, headers=headers)
            try:
                data = json.loads(res.text)
                return data
            except ValueError as e:
                utils.log('Error parsing JSON, response is {0}'
                          .format(res.text))
                raise e
