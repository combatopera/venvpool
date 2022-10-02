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

from argparse import ArgumentParser
from contextlib import contextmanager
from tempfile import mkdtemp, mkstemp
import errno, logging, operator, os, re, shutil, subprocess, sys

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

def safe_name(name, unsafeseq = re.compile('[^A-Za-z0-9.]+')):
    return unsafeseq.sub('-', name)

def to_filename(name):
    return name.replace('-', '_')

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

    def createortrywritelock(self):
        try:
            _osop(os.mkdir, os.path.dirname(self.readlocks))
            return True
        except oserrors[errno.EEXIST]:
            return self.trywritelock()

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
        pyname, = (n for n in os.listdir(libpath) if n.startswith('python'))
        return os.path.join(libpath, pyname, 'site-packages')

    def __init__(self, venvpath):
        super(Venv, self).__init__(venvpath)
        self.venvpath = venvpath

    def create(self, pyversion):
        def isolated(*command):
            subprocess.check_call(command, cwd = tempdir, stdout = sys.stderr)
        executable = "python%s" % pyversion
        absvenvpath = os.path.abspath(self.venvpath)
        with TemporaryDirectory() as tempdir:
            if pyversion < 3:
                isolated('virtualenv', '-p', executable, absvenvpath)
            else:
                isolated(executable, '-m', 'venv', absvenvpath)
                isolated(os.path.join(absvenvpath, 'bin', 'pip'), 'install', '--upgrade', 'pip', 'setuptools', 'wheel')

    def delete(self):
        log.debug("Delete transient venv: %s", self.venvpath)
        shutil.rmtree(self.venvpath)

    def programpath(self, name):
        return os.path.join(self.venvpath, 'bin', name)

    def install(self, args, pip = None):
        log.debug("Install: %s", ' '.join(args))
        if args:
            if pip is None:
                Pip(self.programpath('pip')).pipinstall(args)
            else:
                Pip(pip).pipinstall(args + ['--prefix', self.venvpath])

    def compatible(self, installdeps):
        for i in installdeps.volatileprojects:
            if not self._hasvolatileproject(i):
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

    def _hasvolatileproject(self, info):
        return os.path.exists(os.path.join(self.site_packages, "%s-%s.dist-info" % (to_filename(safe_name(info.config.name)), info.devversion())))

    def _haseditableproject(self, info):
        path = os.path.join(self.site_packages, "%s.egg-link" % safe_name(info.config.name))
        if os.path.exists(path):
            with open(path) as f:
                # Assume it isn't a URI relative to site-packages:
                return os.path.abspath(info.projectdir) == f.read().splitlines()[0]

    def _reqversionornone(self, name):
        patterns = [re.compile(format % nameregex) for nameregex in [re.escape(to_filename(safe_name(name)).lower())] for format in [
            "^%s-(.+)[.]dist-info$",
            "^%s-([^-]+).*[.]egg-info$"]]
        for lowername in (n.lower() for n in os.listdir(self.site_packages)):
            for p in patterns:
                m = p.search(lowername)
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
        try:
            _osop(os.makedirs, self.versiondir)
        except oserrors[errno.EEXIST]:
            pass
        venv = Venv(mkdtemp(dir = self.versiondir, prefix = 'venv'))
        with _onerror(venv.delete):
            venv.create(self.pyversion)
            installdeps.invoke(venv)
            assert venv.compatible(installdeps) # Bug if not.
            return venv

    def _lockcompatiblevenv(self, trylock, installdeps):
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
            t = self._lockcompatiblevenv(Venv.tryreadlock, installdeps)
            if t is not None:
                venv, readlock = t
                break
            venv = self._newvenv(installdeps)
            # XXX: Would it be possible to atomically convert write lock to read lock?
            venv.writeunlock()
            readlock = venv.tryreadlock()
            if readlock is not None:
                break
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
        t = self._lockcompatiblevenv(trywritelock, installdeps)
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
        from pkg_resources import parse_requirements # Expensive module!
        return [cls(parsed) for parsed in parse_requirements(lines)]

    @property
    def namepart(self):
        return self.parsed.name

    @property
    def reqstr(self):
        return str(self.parsed)

    def __init__(self, parsed):
        self.parsed = parsed

class FastReq:

    class Version:

        def __init__(self, operator, splitversion):
            self.operator = operator
            self.splitversion = splitversion

        def accept(self, splitversion):
            def pad(v):
                return v + [0] * (n - len(v))
            versions = [splitversion, self.splitversion]
            n = max(map(len, versions))
            return self.operator(*map(pad, versions))

    @staticmethod
    def _splitversion(versionstr):
        return [int(k) for k in versionstr.split('.')]

    s = r'\s*'
    name = '([A-Za-z0-9._-]+)' # Slightly more lenient than PEP 508.
    version = "(<|<=|!=|==|>=|>){s}([0-9.]+)".format(**locals()) # Subset of features.
    versionmatch = re.compile("^{s}{version}{s}$".format(**locals())).search
    getmatch = re.compile("^{s}{name}{s}({version}{s}(?:,{s}{version}{s})*)?$".format(**locals())).search
    del s, name, version
    operators = {
        '<': operator.lt,
        '<=': operator.le,
        '!=': operator.ne,
        '==': operator.eq,
        '>=': operator.ge,
        '>': operator.gt,
    }

    @classmethod
    def parselines(cls, lines):
        def g():
            for line in lines:
                namepart, versionspec = cls.getmatch(line).groups()[:2]
                versions = []
                reqstrversions = []
                if versionspec is not None:
                    for onestr in versionspec.split(','):
                        operatorstr, versionstr = cls.versionmatch(onestr).groups()
                        versions.append(cls.Version(cls.operators[operatorstr], cls._splitversion(versionstr)))
                        reqstrversions.append(operatorstr + versionstr)
                yield cls(namepart, versions, namepart + ','.join(sorted(reqstrversions)))
        return list(g())

    @property
    def parsed(self):
        return self

    def __init__(self, namepart, versions, reqstr):
        self.namepart = namepart
        self.versions = versions
        self.reqstr = reqstr

    def __contains__(self, versionstr):
        splitversion = self._splitversion(versionstr)
        return all(v.accept(splitversion) for v in self.versions)

class SimpleInstallDeps:

    editableprojects = volatileprojects = ()

    def __init__(self, requires, pip = None, reqcls = BaseReq):
        self.pypireqs = reqcls.parselines(requires)
        self.pip = pip

    def invoke(self, venv):
        venv.install([r.reqstr for r in self.pypireqs], self.pip)

def _launch():
    initlogging()
    parser = ArgumentParser(add_help = False)
    parser.add_argument('--pip')
    parser.add_argument('scriptpath', type = os.path.abspath)
    args, scriptargs = parser.parse_known_args()
    Launch(args.pip).launch(True, args.scriptpath, scriptargs)

class Launch:

    @staticmethod
    def _requirementspathornone(projectdir):
        def requirementspaths():
            yield os.path.join(projectdir, 'requirements.txt')
            for name in sorted(os.listdir(projectdir)):
                if name.endswith('.egg-info'):
                    yield os.path.join(projectdir, name, 'requires.txt')
        for requirementspath in requirementspaths():
            if os.path.exists(requirementspath):
                return requirementspath

    def __init__(self, pipornone):
        self.pipornone = pipornone

    def launch(self, execflag, scriptpath, scriptargs):
        assert scriptpath.endswith(dotpy)
        projectdir = os.path.dirname(scriptpath)
        while True:
            requirementspath = self._requirementspathornone(projectdir)
            if requirementspath is not None:
                break
            if os.path.exists(os.path.join(projectdir, 'project.arid')):
                self.launch(False, os.path.join(os.path.dirname(__file__), 'boot', 'pipify.py'), [projectdir])
                requirementspath = self._requirementspathornone(projectdir)
                break
            parent = os.path.dirname(projectdir)
            if parent == projectdir:
                sys.exit('No requirements found.')
            projectdir = parent
        log.debug("Found requirements: %s", requirementspath)
        with open(requirementspath) as f:
            installdeps = SimpleInstallDeps(f.read().splitlines(), self.pipornone, FastReq)
        module = os.path.relpath(scriptpath[:-len(dotpy)], projectdir).replace(os.sep, '.')
        with Pool(sys.version_info.major).readonly(installdeps) as venv:
            bindir = os.path.join(venv.venvpath, 'bin')
            argv = [os.path.join(bindir, 'python'), '-c', """import os, runpy, sys
assert not sys.path[0]
sys.path[0] = %r
# TODO: Test insertion logic.
i = len(sys.path)
suffix = os.sep + 'site-packages'
while sys.path[i - 1].endswith(suffix):
    i -= 1
sys.path.insert(i, %r)
runpy.run_module(%r, run_name = '__main__', alter_sys = True)""" % (bindir, projectdir, module)] + scriptargs
            if execflag:
                os.execv(argv[0], argv)
            subprocess.check_call(argv)

if '__main__' == __name__:
    _launch()
