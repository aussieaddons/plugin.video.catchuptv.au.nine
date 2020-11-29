from __future__ import absolute_import, unicode_literals

import io
import json
import os
import re

try:
    import mock
except ImportError:
    import unittest.mock as mock

import testtools

import responses

import resources.lib.comm as comm
import resources.lib.config as config


class CommTests(testtools.TestCase):
    @classmethod
    def setUpClass(self):
        cwd = os.path.join(os.getcwd(), 'resources/tests')
        with open(os.path.join(cwd, 'fakes/json/episodes.json'), 'rb') as f:
            self.EPISODES_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/genres.json'), 'rb') as f:
            self.GENRES_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/livestreams.json'), 'rb') as f:
            self.LIVESTREAMS_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/series_query.json'),
                  'rb') as f:
            self.SERIES_QUERY_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/tv-series.json'), 'rb') as f:
            self.TV_SERIES_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/video.json'), 'rb') as f:
            self.VIDEO_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/video_drm.json'), 'rb') as f:
            self.VIDEO_DRM_JSON = io.BytesIO(f.read()).read()

    @responses.activate
    def test_fetch_bc_url(self):
        responses.add('GET', 'http://foo.bar', body='{"foo":"bar"}')
        observed = comm.fetch_bc_url('http://foo.bar')
        expected = {'foo': 'bar'}
        self.assertEqual(expected, observed)

    @responses.activate
    def test_list_series_nocache(self):
        responses.add('GET', config.TVSERIES_URL, body=self.TV_SERIES_JSON)
        observed = comm.list_series()
        self.assertEqual(802, len(observed))
        self.assertEqual('100 Day Dream Home', observed[0].title)

    @responses.activate
    def test_list_series_by_genre(self):
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/pages/genres/'),
                      body=self.SERIES_QUERY_JSON)
        responses.add('GET', config.TVSERIES_URL, body=self.TV_SERIES_JSON)
        observed = comm.list_series_by_genre('aussie-drama')
        self.assertEqual(23, len(observed))
        self.assertEqual('bad-mothers', observed[0])

    @responses.activate
    def test_list_genres(self):
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/genres\?'),
                      body=self.GENRES_JSON)
        observed = comm.list_genres()
        self.assertEqual(26, len(observed))
        self.assertEqual('Aussie Drama', observed[1].title)

    @responses.activate
    def test_list_episodes(self):
        params = {'episode': '',
                  'episode_slug': '',
                  'season_slug': 'season-1',
                  'series_slug': 'bad-mothers'}
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/pages/tv-ser'),
                      body=self.EPISODES_JSON)
        observed = comm.list_episodes(params)
        self.assertEqual(8, len(observed))
        self.assertEqual('Ep 1 - Episode 1', observed[0].title)

    @responses.activate
    def test_get_next_episode(self):
        params = {'episode': '',
                  'episode_no': '1',
                  'episode_slug': '',
                  'season_slug': 'season-1',
                  'series_slug': 'bad-mothers'}
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/pages/tv-ser'),
                      body=self.EPISODES_JSON)
        observed = comm.get_next_episode(params)
        self.assertEqual('Ep 2 - Episode 2', observed.title)

    @responses.activate
    def test_list_live(self):
        responses.add('GET', config.LIVETV_URL, body=self.LIVESTREAMS_JSON)
        observed = comm.list_live({})
        self.assertEqual(5, len(observed))
        self.assertEqual('Channel 9', observed[0].title)

    def test_get_subtitles(self):
        text_tracks = json.loads(self.VIDEO_JSON).get('text_tracks')
        observed = comm.get_subtitles(text_tracks)
        self.assertEqual(True, observed.endswith('826335af'))

    @responses.activate
    def test_get_stream_not_live(self):
        responses.add('GET', re.compile('https://edge.api.brightcove.com/'),
                      body=self.VIDEO_JSON)
        url = config.BRIGHTCOVE_DRM_URL.format(config.BRIGHTCOVE_ACCOUNT, '42')
        observed = comm.get_stream(url)
        self.assertIn('713677e9', observed.get('url'))
        self.assertIn('text.vtt', observed.get('sub_url'))

    @responses.activate
    def test_get_widevine_auth(self):
        responses.add('GET', re.compile('https://edge.api.brightcove.com/'),
                      body=self.VIDEO_DRM_JSON)
        url = config.BRIGHTCOVE_DRM_URL.format(config.BRIGHTCOVE_ACCOUNT, '42')
        observed = comm.get_widevine_auth(url)
        self.assertIn('50b2d5f3', observed.get('url'))
        self.assertIsNone(observed.get('sub_url'))
        self.assertIn('6d942af9', observed.get('key'))
