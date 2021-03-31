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

from .util import cachedir, onerror, TemporaryDirectory
from contextlib import contextmanager
from pkg_resources import safe_name, to_filename
from tempfile import mkdtemp
import errno, logging, os, re, shutil, subprocess, sys

log = logging.getLogger(__name__)
pooldir = os.path.join(cachedir, 'pool')

class Pip:

    envpatch = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')
    envimage = dict(os.environ, **envpatch)

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = self.envimage, stdout = sys.stderr)

    def installeditable(self, solution, infos):
        log.debug("Install solution: %s", ' '.join(solution))
        self.pipinstall(solution)
        log.debug("Install editable: %s", ' '.join(safe_name(i.config.name) for i in infos))
        self.pipinstall(['--no-deps'] + sum((['-e', i.projectdir] for i in infos), []))

class Venv:

    @property
    def site_packages(self):
        libpath = os.path.join(self.venvpath, 'lib')
        pyname, = os.listdir(libpath)
        return os.path.join(libpath, pyname, 'site-packages')

    def __init__(self, venvpath):
        self.tokenpath = os.path.join(venvpath, 'token')
        self.venvpath = venvpath

    def create(self, pyversion):
        with TemporaryDirectory() as tempdir:
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, os.path.abspath(self.venvpath)], cwd = tempdir, stdout = sys.stderr)

    def unlock(self):
        os.mkdir(self.tokenpath)

    def trylock(self):
        try:
            os.rmdir(self.tokenpath)
            return True
        except OSError as e:
            if errno.ENOENT != e.errno:
                raise

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
def poolsession(transient):
    @contextmanager
    def openvenv(pyversion, installdeps):
        versiondir = os.path.join(pooldir, str(pyversion))
        os.makedirs(versiondir, exist_ok = True)
        for name in [] if transient else sorted(os.listdir(versiondir)):
            venv = Venv(os.path.join(versiondir, name))
            if venv.trylock():
                with onerror(venv.unlock):
                    if venv.compatible(installdeps):
                        break
                venv.unlock()
        else:
            venv = Venv(mkdtemp(dir = versiondir))
            with onerror(venv.delete):
                venv.create(pyversion)
                installdeps(venv)
            if not transient:
                newvenvs.append(venv)
        try:
            yield venv
        finally:
            (venv.delete if transient else venv.unlock)()
    newvenvs = []
    yield openvenv
    if newvenvs:
        _compactpool()

def _compactpool(): # XXX: Combine venvs with orthogonal dependencies?
    jdupes = shutil.which('jdupes')
    if jdupes is None:
        log.debug("Skip compact venvs as jdupes not available.")
        return
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
        log.debug("Compact %s venvs.", len(locked))
        # FIXME: Exclude paths that may be overwritten e.g. scripts.
        subprocess.check_call([jdupes, '-Lrq'] + [l.venvpath for l in locked])
    finally:
        for l in reversed(locked):
            l.unlock()
