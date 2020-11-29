from __future__ import absolute_import, unicode_literals

import importlib
import io
import os
import re
import sys

try:
    import mock
except ImportError:
    import unittest.mock as mock

import responses

import testtools

import resources.lib.config as config
from resources.tests.fakes import fakes


class MenuTests(testtools.TestCase):
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

    def setUp(self):
        super(MenuTests, self).setUp()
        self.mock_plugin = fakes.FakePlugin()
        self.patcher = mock.patch.dict('sys.modules',
                                       xbmcplugin=self.mock_plugin)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        global menu
        menu = importlib.import_module('resources.lib.menu')

    def tearDown(self):
        super(MenuTests, self).tearDown()
        self.patcher.stop()
        self.mock_plugin = None

    @mock.patch('resources.lib.classes.utils.get_kodi_major_version')
    @mock.patch('xbmcgui.ListItem')
    @mock.patch('sys.argv', ['plugin://plugin.video.catchuptv.au.nine/', '5',
                             '',
                             'resume:false'])
    @responses.activate
    def test_list_categories(self, mock_listitem, mock_version):
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/genres\\?'),
                      body=self.GENRES_JSON)
        mock_listitem.side_effect = fakes.FakeListItem
        mock_version.return_value = 17
        menu.list_categories()
        self.assertEqual(29, len(self.mock_plugin.directory))
        self.assertEqual('Live TV', self.mock_plugin.directory[0].get(
            'listitem').getLabel())
        self.assertEqual('Settings', self.mock_plugin.directory[-1].get(
            'listitem').getLabel())

    @mock.patch('resources.lib.classes.utils.get_kodi_major_version')
    @mock.patch('xbmcgui.ListItem')
    @mock.patch('sys.argv', ['plugin://plugin.video.catchuptv.au.nine/', '5',
                             '?action=listseries&desc=Foo.&genre=Drama'
                             '&genre_slug=drama&season_name=Season%201'
                             '&season_slug=season-1&series_name=Bad%20Mothers'
                             '&series_slug=bad-mothers&title=Bad%20Mothers',
                             'resume:false'])
    @responses.activate
    def test_make_episodes_list(self, mock_listitem, mock_version):
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/pages/'),
                      body=self.EPISODES_JSON)
        mock_listitem.side_effect = fakes.FakeListItem
        mock_version.return_value = 17
        params = menu.utils.get_url(sys.argv[2][1:])
        menu.make_episodes_list(params)
        self.assertEqual(8, len(self.mock_plugin.directory))
        self.assertEqual('Ep 1 - Episode 1', self.mock_plugin.directory[0].get(
            'listitem').getLabel())

    @mock.patch('resources.lib.classes.utils.get_kodi_major_version')
    @mock.patch('xbmcgui.ListItem')
    @mock.patch('sys.argv', ['plugin://plugin.video.catchuptv.au.nine/', '5',
                             '?action=listcategories&category=Live%20TV',
                             'resume:false'])
    @responses.activate
    def test_make_live_list(self, mock_listitem, mock_version):
        responses.add('GET', config.LIVETV_URL, body=self.LIVESTREAMS_JSON)
        mock_listitem.side_effect = fakes.FakeListItem
        mock_version.return_value = 17
        params = menu.utils.get_url(sys.argv[2][1:])
        menu.make_live_list(params)
        self.assertEqual(5, len(self.mock_plugin.directory))
        self.assertEqual('Channel 9', self.mock_plugin.directory[0].get(
            'listitem').getLabel())

    @mock.patch('resources.lib.classes.utils.get_kodi_major_version')
    @mock.patch('xbmcgui.ListItem')
    @mock.patch('sys.argv', ['plugin://plugin.video.catchuptv.au.nine/', '5',
                             '?action=listcategories&category=genre'
                             '&genre=aussie-drama',
                             'resume:false'])
    @responses.activate
    def test_make_series_list(self, mock_listitem, mock_version):
        responses.add('GET', config.TVSERIES_URL, body=self.TV_SERIES_JSON)
        responses.add('GET',
                      re.compile(
                          'https://tv-api.9now.com.au/v2/pages/genres/'),
                      body=self.SERIES_QUERY_JSON)
        mock_listitem.side_effect = fakes.FakeListItem
        mock_version.return_value = 17
        params = menu.utils.get_url(sys.argv[2][1:])
        menu.make_series_list(params)
        self.assertEqual(55, len(self.mock_plugin.directory))
        self.assertEqual('Bad Mothers', self.mock_plugin.directory[0].get(
            'listitem').getLabel())
