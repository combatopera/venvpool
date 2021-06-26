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

from .minivenv import Pip
from .pipify import pipify
from .projectinfo import ProjectInfo
from .setuproot import setuptoolsinfo
from .util import initlogging, ThreadPoolExecutor
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
import logging, os, re, shutil, subprocess, sys

log = logging.getLogger(__name__)
pkg_resources = re.compile(br'\bpkg_resources\b')
eolbytes = set(b'\r\n')
pyversion = sys.version_info.major

def _ispyvenproject(projectdir):
    return os.path.exists(os.path.join(projectdir, ProjectInfo.projectaridname))

def _hasname(info):
    try:
        info.config.name
        return True
    except AttributeError:
        log.debug("Skip: %s", info.projectdir)

def _projectinfos():
    config = ConfigCtrl()
    config.loadsettings()
    projectsdir = config.node.projectsdir
    for p in sorted(os.listdir(projectsdir)):
        projectdir = os.path.join(projectsdir, p)
        if _ispyvenproject(projectdir):
            yield ProjectInfo.seek(projectdir)
        else:
            setuppath = os.path.join(projectdir, 'setup.py')
            if os.path.exists(setuppath):
                if pyversion < 3:
                    log.debug("Ignore: %s", projectdir)
                else:
                    yield setuptoolsinfo(setuppath)

def _prepare(info):
    if _ispyvenproject(info.projectdir):
        log.debug("Prepare: %s", info.projectdir)
        pipify(info)

class ExecutableInfo:

    def __init__(self, venvroot, info):
        self.venvpath = os.path.join(venvroot, 'projects', info.config.name)
        self.info = info

    def exists(self):
        return os.path.exists(self.venvpath)

    def create(self, pyversion):
        subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, self.venvpath])

    def copyfrom(self, that):
        log.info("Copy blank venv to: %s", self.venvpath)
        shutil.copytree(that.venvpath, self.venvpath, symlinks = True)
        subprocess.check_call(['sed', '-i', "s:%s:%s:" % (that.venvpath, self.venvpath)] + list(self.scriptpaths()))

    def install(self):
        binpath = os.path.join(self.venvpath, 'bin')
        Pip(os.path.join(binpath, 'pip')).pipinstall(['-e', self.info.projectdir])
        magic = ("#!%s" % os.path.join(binpath, 'python')).encode()
        for name in os.listdir(binpath):
            path = os.path.join(binpath, name)
            if not os.path.isdir(path):
                with open(path, 'rb') as f:
                    data = f.read(len(magic) + 1)
                if data[:-1] == magic and data[-1] in eolbytes:
                    with open(path, 'rb') as f:
                        data = f.read()
                    with open(path, 'wb') as f:
                        f.write(pkg_resources.sub(b'pkg_resources_lite', data))

    def scriptpaths(self):
        bindir = os.path.join(self.venvpath, 'bin')
        for name in sorted(os.listdir(bindir)):
            yield os.path.join(bindir, name)

def main_initopt():
    'Furnish the venv with editable projects and their dependencies.'
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('-f', action = 'store_true')
    parser.add_argument('venvroot', nargs = '?', default = os.path.join(os.path.dirname(sys.executable), '..', '..', '..'))
    args = parser.parse_args()
    versioninfos = {}
    allinfos = {i.config.name: i for i in _projectinfos() if _hasname(i)}
    def add(i):
        if i not in versioninfos:
            versioninfos[i] = None
            for p in i.localrequires():
                add(allinfos[p])
    for info in allinfos.values():
        if info.config.executable and pyversion in info.config.pyversions:
            add(info)
    executableinfos = [ExecutableInfo(args.venvroot, i) for i in versioninfos if i.config.executable]
    newinfos = [i for i in executableinfos if not i.exists()]
    with ThreadPoolExecutor() as e:
        for future in [e.submit(_prepare, info) for info in versioninfos]:
            future.result()
        if newinfos:
            newinfos[0].create(pyversion)
            for future in [e.submit(i.copyfrom, newinfos[0]) for i in newinfos[1:]]:
                future.result()
                log.debug('Copied.')
    bindir = os.path.join(args.venvroot, 'bin')
    if not os.path.exists(bindir):
        os.mkdir(bindir)
    for k, info in enumerate(executableinfos):
        info.install()
        log.info("Compact %s venvs.", k + 1)
        subprocess.check_call(['jdupes', '-Lrq'] + [i.venvpath for i in executableinfos[:k + 1]])
        for scriptpath in info.scriptpaths():
            linkpath = os.path.join(bindir, os.path.basename(scriptpath))
            if not os.path.exists(linkpath):
                relpath = os.path.relpath(scriptpath, os.path.dirname(linkpath))
                log.info("Symlink %s to: %s", linkpath, relpath)
                os.symlink(relpath, linkpath)
