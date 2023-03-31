# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022, 2023 Andrzej Cichocki

# This file is part of venvpool.
#
# venvpool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# venvpool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with venvpool.  If not, see <http://www.gnu.org/licenses/>.

import sys, time

venvpoolname = 'venvpool'
assert venvpoolname not in sys.modules
mark = time.time()
import venvpool
loadtime = time.time() - mark
assert venvpoolname in sys.modules

from multiprocessing import cpu_count
from pkg_resources import parse_requirements # Expensive module!
from tempfile import mkstemp
from unittest import TestCase
from venvpool import _chunkify, _compress, _decompress, Execute, FastReq, listorempty, LockStateException, oserrors, _osop, ReadLock, TemporaryDirectory, Venv
import errno, inspect, operator, os, subprocess

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
    assert not d.trywritelock() # FIXME: Investigate lsof hang, or try fuser.
    os.kill(childpid, SIGINT)
    os.waitpid(childpid, 0)
    assert d.trywritelock()

class TestVenvPool(TestCase):

    def test_loadtime(self):
        def expr(lhs, op, rhs, strs = {operator.ge: '>=', operator.lt: '<'}):
            sys.stderr.write("%s %s %s ... " % (lhs, strs[op], rhs))
            return op(lhs, rhs)
        if not expr(sys.version_info.major, operator.ge, 3):
            return
        with open('/proc/loadavg') as f:
            if not expr(cpu_count(), operator.ge, float(f.read().split()[0])):
                return
        self.assertTrue(expr(loadtime, operator.lt, .01))

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
            self.assertEqual([], listorempty(d))
            os.mkdir(d)
            self.assertEqual([], listorempty(d))
            with open(os.path.join(d, 'yay'), 'w'):
                pass
            self.assertEqual([os.path.join(d, 'yay')], listorempty(d))

    def test_inherithandle(self):
        with TemporaryDirectory() as tempdir:
            subprocess.check_call([
                sys.executable,
                '-c',
                "%s%s(%r)" % (inspect.getsource(_inherithandle), _inherithandle.__name__, tempdir),
            ], env = dict(os.environ, PYTHONPATH = os.path.dirname(venvpool.__file__)))

    def test_fileglobal(self):
        with TemporaryDirectory() as tempdir:
            scriptpath = os.path.join(tempdir, 'module_name.py')
            with open(scriptpath, 'w') as f:
                f.write('import sys\nprint(sys.modules[__name__].__file__)')
            self.assertEqual(scriptpath + '\n', Venv(os.path.dirname(os.path.dirname(sys.executable))).run('check_output', [tempdir], 'module_name', [], universal_newlines = True))

    def test_insertionpoint(self):
        self.assertEqual(0, Execute._insertionpoint(['ax', 'bx', 'cx'], 'x'))
        self.assertEqual(1, Execute._insertionpoint(['a', 'bx', 'cx'], 'x'))
        self.assertEqual(2, Execute._insertionpoint(['ax', 'b', 'cx'], 'x'))
        self.assertEqual(2, Execute._insertionpoint(['a', 'b', 'cx'], 'x'))
        self.assertEqual(0, Execute._insertionpoint(['ax', 'bx', 'c'], 'x'))
        self.assertEqual(1, Execute._insertionpoint(['a', 'bx', 'c'], 'x'))
        self.assertEqual(0, Execute._insertionpoint(['ax', 'b', 'c'], 'x'))
        self.assertEqual(3, Execute._insertionpoint(['a', 'b', 'c'], 'x'))

    def test_chunkify(self):
        self.assertEqual([], list(_chunkify(5, [])))
        self.assertEqual([[0]], list(_chunkify(5, [0])))
        self.assertEqual([[0, 1, 2, 3, 4]], list(_chunkify(5, [0, 1, 2, 3, 4])))
        self.assertEqual([[0, 1, 2, 3, 4], [5]], list(_chunkify(5, [0, 1, 2, 3, 4, 5])))
        self.assertEqual([[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]], list(_chunkify(5, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])))
        self.assertEqual([[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10]], list(_chunkify(5, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])))

    def test_compress(self):
        c = lambda *paths: list(_compress(paths, '+'))
        self.assertEqual(['-'], c())
        self.assertEqual(['', ''], c(''))
        self.assertEqual(['+', ''], c('+'))
        self.assertEqual(['', 'a'], c('a'))
        self.assertEqual(['+', '', ''], c('+', '+'))
        self.assertEqual(['', '+', 'a'], c('+', 'a'))
        self.assertEqual(['', 'a', '+'], c('a', '+'))
        self.assertEqual(['+', 'a', 'a'], c('+a', '+a'))
        self.assertEqual(['+', 'a', 'b'], c('+a', '+b'))
        self.assertEqual(['a+', 'b', 'b'], c('a+b', 'a+b'))
        self.assertEqual(['a+', 'b', 'c'], c('a+b', 'a+c'))

    def test_decompress(self):
        d = lambda *paths: list(_decompress(paths))
        self.assertEqual([], d('a'))
        self.assertEqual(['ab'], d('a', 'b'))
        self.assertEqual(['ab', 'ac'], d('a', 'b', 'c'))

class BaseReq:

    @classmethod
    def parselines(cls, lines):
        return [cls(parsed) for parsed in parse_requirements(lines)]

    @property
    def namepart(self):
        return self.parsed.name

    @property
    def extras(self):
        return self.parsed.extras

    @property
    def reqstr(self):
        return str(self.parsed)

    def __init__(self, parsed):
        self.parsed = parsed

    def acceptversion(self, versionstr):
        return versionstr in self.parsed

class ReqCase:

    def test_parse(self):
        for r in self.reqcls.parselines([' woo ', 'woo']):
            self.assertEqual('woo', r.namepart)
            self.assertEqual((), r.extras)
            self.assertEqual('woo', r.reqstr)
            self.assertTrue(r.acceptversion('1.2.3'))
            self.assertTrue(r.acceptversion('2.0'))
            self.assertTrue(r.acceptversion('500'))
        for r in self.reqcls.parselines([' W--..__o == 5 ', 'W--..__o==5']):
            self.assertEqual('W--..__o', r.namepart)
            self.assertEqual((), r.extras)
            self.assertEqual('W--..__o==5', r.reqstr)
            self.assertFalse(r.acceptversion('1.2.3'))
            self.assertFalse(r.acceptversion('2.0'))
            self.assertTrue(r.acceptversion('5'))
            self.assertTrue(r.acceptversion('5.0'))
            self.assertTrue(r.acceptversion('5.00'))
        for r in self.reqcls.parselines([' woo == 5.00 ', 'woo==5.00']):
            self.assertEqual('woo', r.namepart)
            self.assertEqual((), r.extras)
            self.assertEqual('woo==5.00', r.reqstr)
            self.assertFalse(r.acceptversion('1.2.3'))
            self.assertFalse(r.acceptversion('2.0'))
            self.assertTrue(r.acceptversion('5'))
            self.assertTrue(r.acceptversion('5.0'))
            self.assertTrue(r.acceptversion('5.00'))
        for r in self.reqcls.parselines([' yay >= 2 , < 3 ', 'yay>=2,<3']):
            self.assertEqual('yay', r.namepart)
            self.assertEqual((), r.extras)
            self.assertEqual('yay<3,>=2', r.reqstr)
            self.assertFalse(r.acceptversion('1.9'))
            self.assertTrue(r.acceptversion('2'))
            self.assertTrue(r.acceptversion('2.9'))
            self.assertFalse(r.acceptversion('3'))
        for r in self.reqcls.parselines(['foo[bar]', ' foo [ bar ] ']):
            self.assertEqual('foo', r.namepart)
            self.assertEqual(('bar',), r.extras)
            self.assertEqual('foo[bar]', r.reqstr)
        for r in self.reqcls.parselines(['foo[bar,baz]', ' foo [ bar , baz ] ', 'foo[baz,bar,bar]']):
            self.assertEqual('foo', r.namepart)
            self.assertTrue(r.extras in [('bar', 'baz'), ('baz', 'bar')])
            self.assertEqual('foo[bar,baz]', r.reqstr)
        for r in self.reqcls.parselines(['foo[]', ' foo [ ] ']):
            self.assertEqual('foo', r.namepart)
            self.assertEqual((), r.extras)
            self.assertEqual('foo', r.reqstr)

class TestFastReq(TestCase, ReqCase):

    reqcls = FastReq

class TestBaseReq(TestCase, ReqCase):

    reqcls = BaseReq
