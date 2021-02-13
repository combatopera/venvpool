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

from .fastfreeze import fastfreeze
from .util import cachedir, TemporaryDirectory
from contextlib import contextmanager
from pkg_resources import safe_name
from tempfile import mkdtemp
import errno, logging, os, shutil, subprocess

log = logging.getLogger(__name__)
pooldir = os.path.join(cachedir, 'pool')

class Pip:

    envpatch = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')
    envimage = dict(os.environ, **envpatch)

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = self.envimage)

    def installeditable(self, solution, infos):
        log.debug("Install solution: %s", ' '.join(solution))
        self.pipinstall(solution)
        log.debug("Install editable: %s", ' '.join(safe_name(i.config.name) for i in infos))
        self.pipinstall(['--no-deps'] + sum((['-e', i.projectdir] for i in infos), []))

class Venv:

    def __init__(self, venvpath, pyversionornone):
        if pyversionornone is not None:
            with TemporaryDirectory() as tempdir:
                subprocess.check_call(['virtualenv', '-p', "python%s" % pyversionornone, os.path.abspath(venvpath)], cwd = tempdir)
        self.tokenpath = os.path.join(venvpath, 'token')
        self.venvpath = venvpath

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
        from .projectinfo import Req
        if installdeps.volatileprojects: # TODO: Support this.
            return
        editableprojects = set()
        pypireqs = []
        for name, version in fastfreeze(self.venvpath):
            if '-e' == version:
                editableprojects.add(name)
            else:
                pypireqs.append("%s==%s" % (name, version))
        pypireqs = dict(r.keyversion() for r in Req.parsemany(pypireqs))
        # TODO: For editable projects check it's the same directory.
        if all(i.config.name in editableprojects for i in installdeps.editableprojects) and all(r.parsed.key in pypireqs and pypireqs[r.parsed.key] in r.parsed for r in installdeps.pypireqs):
            log.debug("Found compatible venv: %s", self.venvpath)
            return True

@contextmanager
def _unlockonerror(venv):
    try:
        yield venv
    except:
        venv.unlock()
        raise

@contextmanager
def openvenv(pyversion, installdeps, transient = False):
    versiondir = os.path.join(pooldir, str(pyversion))
    os.makedirs(versiondir, exist_ok = True)
    for name in [] if transient else sorted(os.listdir(versiondir)):
        venv = Venv(os.path.join(versiondir, name), None)
        if venv.trylock():
            with _unlockonerror(venv):
                if venv.compatible(installdeps):
                    poolmodified = False
                    break
            venv.unlock()
    else:
        venv = Venv(mkdtemp(dir = versiondir), pyversion)
        with _unlockonerror(venv):
            installdeps(venv)
        poolmodified = not transient
    try:
        yield venv
    finally:
        venv.delete() if transient else venv.unlock()
    if poolmodified:
        compactpool()

def compactpool():
    locked = []
    try:
        for version in sorted(os.listdir(pooldir)):
            versiondir = os.path.join(pooldir, version)
            for name in sorted(os.listdir(versiondir)):
                venv = Venv(os.path.join(versiondir, name), None)
                if venv.trylock():
                    locked.append(venv)
        jdupes = shutil.which('jdupes')
        if jdupes is not None:
            log.debug("Compact %s venvs.", len(locked))
            subprocess.check_call([jdupes, '-Lrq'] + [l.venvpath for l in locked])
        else:
            log.debug("Skip compact venvs as jdupes not available.")
    finally:
        for l in reversed(locked):
            l.unlock()
