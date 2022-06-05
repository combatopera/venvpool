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

from .minivenv import _listorempty, LockStateException, oserrors, _osop, ReadLock, TemporaryDirectory
from tempfile import mkstemp
from unittest import TestCase
import errno, os

class TestMiniVenv(TestCase):

    def test_oserrors(self):
        with TemporaryDirectory() as tempdir:
            try:
                _osop(os.rmdir, os.path.join(tempdir, 'does-not-exist'))
            except oserrors[errno.ENOENT] as e:
                self.assertEqual(errno.ENOENT, e.errno)
            else:
                self.fail()

    def test_readlock(self):
        h, p = mkstemp()
        try:
            lock = ReadLock(None, h)
            lock.unlock()
            with self.assertRaises(LockStateException):
                lock.unlock()
        finally:
            os.remove(p)
            try:
                os.close(h)
            except OSError:
                pass

    def test_listorempty(self):
        with TemporaryDirectory() as tempdir:
            d = os.path.join(tempdir, 'woo')
            self.assertEqual([], _listorempty(d))
            os.mkdir(d)
            self.assertEqual([], _listorempty(d))
            with open(os.path.join(d, 'yay'), 'w'):
                pass
            self.assertEqual([os.path.join(d, 'yay')], _listorempty(d))
