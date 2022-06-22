# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022 Andrzej Cichocki

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

from tempfile import mkstemp
from unittest import TestCase
from venvpool import _listorempty, LockStateException, oserrors, _osop, ReadLock, TemporaryDirectory
import errno, inspect, os, subprocess, sys, venvpool

def _inherithandle(tempdir):
    from signal import SIGINT
    from venvpool import SharedDir
    import os, sys, time
    flag = os.path.join(tempdir, 'flag')
    p = os.path.join(tempdir, 'shared')
    os.mkdir(p)
    d = SharedDir(p)
    d.writeunlock()
    lock = d.tryreadlock()
    childpid = os.fork()
    if not childpid:
        os.execl(sys.executable, sys.executable, '-c', "import os, time\nos.mkdir(%r)\nwhile True: time.sleep(1)" % flag)
    while not os.path.exists(flag):
        time.sleep(.1)
    lock.unlock()
    assert not d.trywritelock()
    os.kill(childpid, SIGINT)
    os.waitpid(childpid, 0)
    assert d.trywritelock()

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
            lock = ReadLock(h)
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

    def test_inherithandle(self):
        with TemporaryDirectory() as tempdir:
            subprocess.check_call([
                sys.executable,
                '-c',
                "%s%s(%r)" % (inspect.getsource(_inherithandle), _inherithandle.__name__, tempdir),
            ])

    def test_fileglobal(self):
        with TemporaryDirectory() as tempdir:
            open(os.path.join(tempdir, 'requirements.txt'), 'w').close()
            scriptpath = os.path.join(tempdir, 'module.py')
            with open(scriptpath, 'w') as f:
                f.write('import sys\nprint(sys.modules[__name__].__file__)')
            self.assertEqual(scriptpath + '\n', subprocess.check_output(["python%s" % sys.version_info.major, venvpool.__file__, scriptpath], universal_newlines = True))
