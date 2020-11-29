from __future__ import absolute_import, unicode_literals

import io
import os
import json

from collections import OrderedDict
from datetime import datetime

try:
    import mock
except ImportError:
    import unittest.mock as mock

import testtools

import resources.lib.classes as classes

from resources.tests.fakes import fakes

class ClassesBaseItemTests(testtools.TestCase):
    def test_repr(self):
        g = classes.Genre(title='foo')
        g_repr = 'classes.' + repr(g)
        new_g = eval(g_repr)
        self.assertEqual(repr(g), repr(new_g))


class ClassesCacheObjTests(testtools.TestCase):
    @classmethod
    def setUpClass(self):
        cwd = os.path.join(os.getcwd(), 'resources/tests')
        with open(os.path.join(cwd, 'fakes/json/tv-series.json'), 'rb') as f:
            self.TV_SERIES_JSON = io.BytesIO(f.read()).read()

    @mock.patch('xbmcgui.Window')
    def test_getData(self, mock_window):
        window = fakes.FakeWindow()
        mock_window.return_value = window
        now = datetime.now()
        cached_data = (now, json.loads(self.TV_SERIES_JSON))
        window.setProperty('%s|%s' % ('foo', 'http://foo.bar'), repr(cached_data))
        cache = classes.CacheObj()
        observed = cache.getData('http://foo.bar', name='foo')
        self.assertEqual(json.loads(self.TV_SERIES_JSON), observed)