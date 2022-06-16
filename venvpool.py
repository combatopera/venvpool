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

from contextlib import contextmanager
from pkg_resources import parse_requirements, safe_name, to_filename
from tempfile import mkdtemp, mkstemp
import errno, logging, os, re, shutil, subprocess, sys

log = logging.getLogger(__name__)
cachedir = os.path.join(os.path.expanduser('~'), '.cache', 'pyven') # TODO: Honour XDG_CACHE_HOME.
dotpy = '.py'
oserrors = {code: type(name, (OSError,), {}) for code, name in errno.errorcode.items()}
pooldir = os.path.join(cachedir, 'pool')
try:
    set_inheritable = os.set_inheritable
except AttributeError:
    from fcntl import fcntl, FD_CLOEXEC, F_GETFD, F_SETFD
    def set_inheritable(h, inherit):
        assert inherit
        fcntl(h, F_SETFD, fcntl(h, F_GETFD) & ~FD_CLOEXEC)

def _osop(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except OSError as e:
        raise oserrors[e.errno](*e.args)

def initlogging():
    logging.basicConfig(format = "%(asctime)s %(levelname)s %(message)s", level = logging.DEBUG)

@contextmanager
def TemporaryDirectory():
    tempdir = mkdtemp()
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)

@contextmanager
def _onerror(f):
    try:
        yield
    except:
        f()
        raise

class Pip:

    envpatch = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = dict(os.environ, **self.envpatch), stdout = sys.stderr)

def _listorempty(d, xform = lambda p: p):
    try:
        names = _osop(os.listdir, d)
    except oserrors[errno.ENOENT]:
        return []
    return [xform(os.path.join(d, n)) for n in sorted(names)]

class LockStateException(Exception): pass

class ReadLock:

    def __init__(self, handle):
        self.handle = handle

    def unlock(self):
        try:
            _osop(os.close, self.handle)
        except oserrors[errno.EBADF]:
            raise LockStateException

def _idempotentunlink(path):
    try:
        _osop(os.remove, path)
        return True
    except oserrors[errno.ENOENT]:
        pass

if '/' == os.sep:
    def _swept(readlocks):
        if readlocks:
            # Check stderr instead of returncode for errors:
            stdout, stderr = subprocess.Popen(['lsof', '-t'] + readlocks, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
            if not stderr and not stdout:
                for readlock in readlocks:
                    if _idempotentunlink(readlock):
                        yield readlock
else:
    def _swept(readlocks): # TODO: Untested!
        for readlock in readlocks:
            try:
                if _idempotentunlink(readlock):
                    yield readlock
            except oserrors[errno.EACCES]:
                pass

class SharedDir(object):

    def __init__(self, dirpath):
        self.readlocks = os.path.join(dirpath, 'readlocks')

    def _sweep(self):
        for readlock in _swept(_listorempty(self.readlocks)):
            log.debug("Swept: %s", readlock)

    def trywritelock(self):
        self._sweep()
        try:
            _osop(os.rmdir, self.readlocks)
            return True
        except (oserrors[errno.ENOENT], oserrors[errno.ENOTEMPTY]):
            pass

    def writeunlock(self):
        try:
            _osop(os.mkdir, self.readlocks)
        except oserrors[errno.EEXIST]:
            raise LockStateException

    def tryreadlock(self):
        try:
            h = _osop(mkstemp, dir = self.readlocks, prefix = 'lock')[0]
            set_inheritable(h, True)
            return ReadLock(h)
        except oserrors[errno.ENOENT]:
            pass

class Venv(SharedDir):

    @property
    def site_packages(self):
        libpath = os.path.join(self.venvpath, 'lib')
        pyname, = os.listdir(libpath)
        return os.path.join(libpath, pyname, 'site-packages')

    def __init__(self, venvpath):
        super(Venv, self).__init__(venvpath)
        self.venvpath = venvpath

    def create(self, pyversion):
        with TemporaryDirectory() as tempdir:
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, os.path.abspath(self.venvpath)], cwd = tempdir, stdout = sys.stderr)

    def delete(self):
        log.debug("Delete transient venv: %s", self.venvpath)
        shutil.rmtree(self.venvpath)

    def programpath(self, name):
        return os.path.join(self.venvpath, 'bin', name)

    def install(self, args):
        log.debug("Install: %s", ' '.join(args))
        if args:
            Pip(self.programpath('pip')).pipinstall(args)

    def compatible(self, installdeps):
        if installdeps.volatileprojects: # TODO: Support this.
            return
        for i in installdeps.editableprojects:
            if not self._haseditableproject(i): # FIXME LATER: It may have new requirements.
                return
        for r in installdeps.pypireqs:
            version = self._reqversionornone(r.namepart)
            if version is None or version not in r.parsed:
                return
        log.debug("Found compatible venv: %s", self.venvpath)
        return True

    def _haseditableproject(self, info):
        path = os.path.join(self.site_packages, "%s.egg-link" % safe_name(info.config.name))
        if os.path.exists(path):
            with open(path) as f:
                # Assume it isn't a URI relative to site-packages:
                return os.path.abspath(info.projectdir) == f.read().splitlines()[0]

    def _reqversionornone(self, name):
        pattern = re.compile("^%s-(.+)[.](?:dist|egg)-info$" % re.escape(to_filename(safe_name(name))))
        for name in os.listdir(self.site_packages):
            m = pattern.search(name)
            if m is not None:
                return m.group(1)

class Pool:

    @property
    def versiondir(self):
        return os.path.join(pooldir, str(self.pyversion))

    def __init__(self, pyversion):
        self.readonlyortransient = {
            False: self.readonly,
            True: self._transient,
        }
        self.readonlyorreadwrite = {
            False: self.readonly,
            True: self.readwrite,
        }
        self.pyversion = pyversion

    def _newvenv(self, installdeps):
        os.makedirs(self.versiondir, exist_ok = True)
        venv = Venv(mkdtemp(dir = self.versiondir, prefix = 'venv'))
        with _onerror(venv.delete):
            venv.create(self.pyversion)
            installdeps.invoke(venv)
            return venv

    def _compatiblevenv(self, trylock, installdeps):
        for venv in _listorempty(self.versiondir, Venv):
            lock = trylock(venv)
            if lock is not None:
                with _onerror(lock.unlock):
                    if venv.compatible(installdeps):
                        return venv, lock
                lock.unlock()

    @contextmanager
    def _transient(self, installdeps):
        venv = self._newvenv(installdeps)
        try:
            yield venv
        finally:
            venv.delete()

    @contextmanager
    def readonly(self, installdeps):
        while True:
            t = self._compatiblevenv(Venv.tryreadlock, installdeps)
            if t is not None:
                venv, readlock = t
                break
            self._newvenv(installdeps).writeunlock() # TODO: Infinite loop if compatibility check fails.
        try:
            yield venv
        finally:
            readlock.unlock()

    @contextmanager
    def readwrite(self, installdeps):
        def trywritelock(venv):
            if venv.trywritelock():
                class WriteLock:
                    def unlock(self):
                        venv.writeunlock()
                return WriteLock()
        t = self._compatiblevenv(trywritelock, installdeps)
        if t is None:
            venv = self._newvenv(installdeps)
        else:
            venv = t[0]
            with _onerror(venv.writeunlock):
                for dirpath, dirnames, filenames in os.walk(venv.venvpath):
                    for name in filenames:
                        p = os.path.join(dirpath, name)
                        if 1 != os.stat(p).st_nlink:
                            h, q = mkstemp(dir = dirpath)
                            os.close(h)
                            shutil.copy2(p, q)
                            os.remove(p) # Cross-platform.
                            os.rename(q, p)
        try:
            yield venv
        finally:
            venv.writeunlock()

def main_compactpool(): # XXX: Combine venvs with orthogonal dependencies?
    'Use jdupes to combine identical files in the venv pool.'
    initlogging()
    locked = []
    try:
        for versiondir in _listorempty(pooldir):
            for venv in _listorempty(versiondir, Venv):
                if venv.trywritelock():
                    locked.append(venv)
                else:
                    log.debug("Busy: %s", venv.venvpath)
        compactvenvs([l.venvpath for l in locked])
    finally:
        for l in reversed(locked):
            l.writeunlock()

def compactvenvs(venvpaths):
    log.info("Compact %s venvs.", len(venvpaths))
    if venvpaths:
        subprocess.check_call(['jdupes', '-Lrq'] + venvpaths)
    log.info('Compaction complete.')

class BaseReq:

    @classmethod
    def parselines(cls, lines):
        return [cls(parsed) for parsed in parse_requirements(lines)]

    @property
    def namepart(self):
        return self.parsed.name

    @property
    def reqstr(self):
        return str(self.parsed)

    def __init__(self, parsed):
        self.parsed = parsed

class SimpleInstallDeps:

    editableprojects = volatileprojects = ()

    def __init__(self, requires):
        self.pypireqs = BaseReq.parselines(requires)

    def invoke(self, venv):
        venv.install([r.reqstr for r in self.pypireqs])

def _launch():
    initlogging()
    scriptpath = os.path.abspath(sys.argv[1])
    scriptargs = sys.argv[2:]
    assert scriptpath.endswith(dotpy)
    projectdir = os.path.dirname(scriptpath)
    while True:
        requirementspath = os.path.join(projectdir, 'requirements.txt')
        if os.path.exists(requirementspath):
            log.debug("Found requirements: %s", requirementspath)
            break
        parent = os.path.dirname(projectdir)
        assert parent != projectdir
        projectdir = parent
    with open(requirementspath) as f:
        installdeps = SimpleInstallDeps(f.read().splitlines())
    module = os.path.relpath(scriptpath[:-len(dotpy)], projectdir).replace(os.sep, '.')
    with Pool(sys.version_info.major).readonly(installdeps) as venv:
        bindir = os.path.join(venv.venvpath, 'bin')
        argv = [os.path.join(bindir, 'python'), '-c', """import runpy, sys
assert not sys.path[0]
sys.path[0] = %r
sys.path.append(%r)
runpy.run_module(%r, run_name = '__main__')""" % (bindir, projectdir, module)] + scriptargs
        os.execv(argv[0], argv)

if '__main__' == __name__:
    _launch()
