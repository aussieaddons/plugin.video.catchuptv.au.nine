from __future__ import absolute_import, unicode_literals

import importlib
import io
import os

try:
    import mock
except ImportError:
    import unittest.mock as mock

import testtools

from resources.tests.fakes import fakes


class DefaultTests(testtools.TestCase):

    @classmethod
    def setUpClass(self):
        cwd = os.path.join(os.getcwd(), 'resources/tests')

    def setUp(self):
        super(DefaultTests, self).setUp()
        self.mock_plugin = fakes.FakePlugin()
        self.patcher = mock.patch.dict('sys.modules',
                                       xbmcplugin=self.mock_plugin)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        for module in ['menu', 'play']:
            setattr(self, module,
                    importlib.import_module(
                        'resources.lib.{0}'.format(module)))
            self.assertEqual(self.mock_plugin,
                             getattr(self, module).xbmcplugin)
        global default
        global classes
        default = importlib.import_module('default')
        classes = importlib.import_module('resources.lib.classes')

    def tearDown(self):
        super(DefaultTests, self).tearDown()
        self.patcher.stop()
        self.mock_plugin = None

    @mock.patch('resources.lib.menu.list_categories')
    @mock.patch('sys.argv',
                ['plugin://plugin.video.catchuptv.au.nine/', '5',
                 '',
                 'resume:false'])
    def test_default_no_params(self, mock_list_categories):
        default.main()
        mock_list_categories.assert_called_with()

    @mock.patch('resources.lib.menu.make_live_list')
    @mock.patch('sys.argv',
                ['plugin://plugin.video.catchuptv.au.nine/', '5',
                 '?action=listcategories&category=Live%20TV',
                 'resume:false'])
    def test_default_live(self, mock_make_live):
        default.main()
        mock_make_live.assert_called_with({'action': 'listcategories',
                                           'category': 'Live TV'})

    @mock.patch('resources.lib.menu.make_series_list')
    @mock.patch('sys.argv',
                ['plugin://plugin.video.catchuptv.au.nine/', '5',
                 '?action=listcategories&category=genre&genre=aussie-drama',
                 'resume:false'])
    def test_default_series_list(self, mock_make_series_list):
        default.main()
        mock_make_series_list.assert_called_with({'action': 'listcategories',
                                                  'category': 'genre',
                                                  'genre': 'aussie-drama'})

    @mock.patch('resources.lib.menu.make_episodes_list')
    @mock.patch('sys.argv',
                ['plugin://plugin.video.catchuptv.au.nine/', '5',
                 '?action=listseries&desc=Foo.&genre=Drama'
                 '&genre_slug=drama&season_name=Season%201'
                 '&season_slug=season-1&series_name=Bad%20Mothers'
                 '&series_slug=bad-mothers&title=Bad%20Mothers',
                 'resume:false'])
    def test_default_episodes_list(self, mock_make_episodes_list):
        default.main()
        mock_make_episodes_list.assert_called_with(
            {'action': 'listseries',
             'desc': 'Foo.',
             'genre': 'Drama',
             'genre_slug': 'drama',
             'season_name': 'Season 1',
             'season_slug': 'season-1',
             'series_name': 'Bad Mothers',
             'series_slug': 'bad-mothers',
             'title': 'Bad Mothers'})

    @mock.patch('resources.lib.play.play_video')
    @mock.patch('sys.argv',
                ['plugin://plugin.video.catchuptv.au.nine/', '5',
                 '?action=listepisodes&airdate=18.02.2019'
                 '&desc=Foo&duration=2424&episode_name=Episode+1'
                 '&episode_no=1&id=cjs7n6427002k0hr05m5x9k7z'
                 '&fanart=foo.jpg&season_no=1&season_slug=season-1'
                 '&series_slug=bad-mothers'
                 '&series_title=Bad+Mothers&thumb=foo.jpg'
                 '&title=Ep+1+-+Episode+1',
                 'resume:false'])
    def test_default_play_video(self, mock_play):
        default.main()
        mock_play.assert_called_with(
            {'action': 'listepisodes',
             'airdate': '18.02.2019',
             'desc': 'Foo',
             'duration': '2424',
             'episode_name': 'Episode 1',
             'episode_no': '1',
             'id': 'cjs7n6427002k0hr05m5x9k7z',
             'fanart': 'foo.jpg',
             'season_no': '1',
             'season_slug': 'season-1',
             'series_slug': 'bad-mothers',
             'series_title': 'Bad Mothers',
             'thumb': 'foo.jpg',
             'title': 'Ep 1 - Episode 1'})
