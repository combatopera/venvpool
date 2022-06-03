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

from contextlib import contextmanager
from pkg_resources import safe_name, to_filename
from tempfile import mkdtemp
import errno, logging, os, re, shutil, subprocess, sys

log = logging.getLogger(__name__)
cachedir = os.path.join(os.path.expanduser('~'), '.cache', 'pyven') # FIXME: Honour XDG_CACHE_HOME.
pooldir = os.path.join(cachedir, 'pool')

def initlogging():
    logging.basicConfig(format = "%(asctime)s [%(levelname)s] %(message)s", level = logging.DEBUG)

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
    envimage = dict(os.environ, **envpatch)

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = self.envimage, stdout = sys.stderr)

class LockStateException(Exception): pass

class SharedDir:

    def __init__(self, dirpath):
        self.readlocks = os.path.join(dirpath, 'token')

    def unlock(self):
        try:
            os.mkdir(self.readlocks)
        except OSError as e:
            if errno.EEXIST != e.errno:
                raise
            raise LockStateException

    def trylock(self):
        try:
            os.rmdir(self.readlocks)
            return True
        except OSError as e:
            if errno.ENOENT != e.errno:
                raise

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

@contextmanager
def openvenv(transient, pyversion, installdeps):
    versiondir = os.path.join(pooldir, str(pyversion))
    os.makedirs(versiondir, exist_ok = True)
    for name in [] if transient else sorted(os.listdir(versiondir)):
        venv = Venv(os.path.join(versiondir, name))
        if venv.trylock():
            with _onerror(venv.unlock):
                if venv.compatible(installdeps):
                    break
            venv.unlock()
    else:
        venv = Venv(mkdtemp(dir = versiondir))
        with _onerror(venv.delete):
            venv.create(pyversion)
            installdeps(venv)
    try:
        yield venv
    finally:
        (venv.delete if transient else venv.unlock)()

def main_compactpool(): # XXX: Combine venvs with orthogonal dependencies?
    'Use jdupes to combine identical files in the pool.'
    initlogging()
    locked = []
    try:
        for version in sorted(os.listdir(pooldir)):
            versiondir = os.path.join(pooldir, version)
            for name in sorted(os.listdir(versiondir)):
                venv = Venv(os.path.join(versiondir, name))
                if venv.trylock():
                    locked.append(venv)
                else:
                    log.debug("Busy: %s", venv.venvpath)
        compactvenvs([l.venvpath for l in locked])
    finally:
        for l in reversed(locked):
            l.unlock()

def compactvenvs(venvpaths):
    log.info("Compact %s venvs.", len(venvpaths))
    if venvpaths:
        # FIXME: Exclude paths that may be overwritten e.g. scripts.
        subprocess.check_call(['jdupes', '-Lrq'] + venvpaths)
