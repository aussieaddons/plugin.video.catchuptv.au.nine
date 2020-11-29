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

from resources.tests.fakes import fakes


class MenuTests(testtools.TestCase):
    @classmethod
    def setUpClass(self):
        cwd = os.path.join(os.getcwd(), 'resources/tests')
        with open(os.path.join(cwd, 'fakes/json/episodes.json'), 'rb') as f:
            self.EPISODES_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/video.json'), 'rb') as f:
            self.VIDEO_JSON = io.BytesIO(f.read()).read()
        with open(os.path.join(cwd, 'fakes/json/video_drm.json'), 'rb') as f:
            self.VIDEO_DRM_JSON = io.BytesIO(f.read()).read()

    def setUp(self):
        super(MenuTests, self).setUp()
        self.mock_plugin = fakes.FakePlugin()
        self.patcher = mock.patch.dict('sys.modules',
                                       xbmcplugin=self.mock_plugin)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        global play
        play = importlib.import_module('resources.lib.play')

    def tearDown(self):
        super(MenuTests, self).tearDown()
        self.patcher.stop()
        self.mock_plugin = None

    @mock.patch('xbmc.executeJSONRPC')
    @mock.patch('xbmcaddon.Addon.getAddonInfo')
    @mock.patch('xbmcaddon.Addon.getSetting')
    @mock.patch('resources.lib.classes.utils.get_kodi_major_version')
    @mock.patch('xbmcgui.ListItem')
    @mock.patch('sys.argv', ['plugin://plugin.video.catchuptv.au.nine/', '5',
                             '?action=listepisodes&airdate=18.02.2019'
                             '&desc=Foo&duration=2424&episode_name=Episode+1'
                             '&episode_no=1&id=cjs7n6427002k0hr05m5x9k7z'
                             '&fanart=foo.jpg&season_no=1&season_slug=season-1'
                             '&series_slug=bad-mothers'
                             '&series_title=Bad+Mothers&thumb=foo.jpg'
                             '&title=Ep+1+-+Episode+1',
                             'resume:false'])
    @responses.activate
    def test_play_video(self, mock_listitem, mock_version, mock_setting,
                        mock_addon_info, mock_rpc):
        responses.add('GET', re.compile('https://edge.api.brightcove.com/'),
                      body=self.VIDEO_JSON)
        responses.add('GET',
                      re.compile('https://tv-api.9now.com.au/v2/pages/'),
                      body=self.EPISODES_JSON)
        mock_listitem.side_effect = fakes.FakeListItem
        mock_version.return_value = 17
        mock_setting.return_value = 1
        mock_addon_info.return_value = 'plugin.video.catchuptv.au.nine'
        mock_rpc.return_value = '{"result": "OK"}'
        params = play.utils.get_url(sys.argv[2][1:])
        play.play_video(params)
