# Copyright 2013, 2014, 2015, 2016, 2017, 2020 Andrzej Cichocki

# This file is part of pyven.
#
# pyven is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyven is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyven.  If not, see <http://www.gnu.org/licenses/>.

from .util import Excludes, tomlquote
from unittest import TestCase
import os

class TestUtil(TestCase):

    def test_tomlquote(self):
        self.assertEqual('"abc\t \x7e\x80"', tomlquote('abc\t \x7e\x80'))
        self.assertEqual(r'"\u005C\u0022"', tomlquote(r'\"'))
        self.assertEqual(r'"\u0000\u0008\u000A\u001F\u007F"', tomlquote('\x00\x08\x0a\x1f\x7f'))

    def test_excludes(self):
        e = Excludes(['**/contrib/*', '**/*_turbo/*'])
        self.assertFalse('contrib' in e)
        self.assertFalse(os.path.join('a', 'contrib') in e)
        self.assertTrue(os.path.join('contrib', 'x') in e)
        self.assertTrue(os.path.join('a', 'contrib', 'x') in e)
        self.assertTrue(os.path.join('a', 'bb', 'contrib', 'x') in e)
        for t in '_turbo', 'w_turbo', 'ww_turbo':
            self.assertFalse(t in e)
            self.assertFalse(os.path.join('a', t) in e)
            self.assertTrue(os.path.join(t, 'x') in e)
            self.assertTrue(os.path.join('a', t, 'x') in e)
            self.assertTrue(os.path.join('a', 'bb', t, 'x') in e)
