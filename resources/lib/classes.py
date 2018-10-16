import urlparse
import urllib
import unicodedata


class genre(object):
    def __init__(self):
        self.fanart = None
        self.thumb = None
        self.title = None
        self.genre_slug = None

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
    def __init__(self):
        self.multi_season = None
        self.fanart = None
        self.thumb = None
        self.series_name = None
        self.series_slug = None
        self.season_name = None
        self.season_slug = None
        self.title = None
        self.genre = None

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
    def __init__(self):
        self.fanart = None
        self.thumb = None
        self.title = None
        self.desc = None
        self.airdate = None
        self.episode_no = None
        self.episode_name = None
        self.url = None
        self.id = None
        self.drm = None
        self.license_url = None
        self.license_key = None

    def get_title(self):
        return 'Ep {0} - {1}'.format(self.episode_no, self.episode_name)

    def get_airdate(self):
        if self.airdate:
            return '{0}.{1}.{2}'.format(self.airdate[8:10],
                                        self.airdate[5:7],
                                        self.airdate[0:4])

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
    def __init__(self):
        self.fanart = None
        self.thumb = None
        self.title = None
        self.desc = None
        self.episode_name = None
        self.url = None
        self.id = None
        self.drm = None

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
