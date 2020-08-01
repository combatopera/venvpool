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

from .pipify import pipify
from .projectinfo import ProjectInfo
from aridity.config import Config
import logging, os, re, subprocess, sys

log = logging.getLogger(__name__)
pkg_resources = re.compile(br'\bpkg_resources\b')
eolbytes = set(b'\r\n')

def _hasname(info): # TODO: Perhaps deduce a default name and install if executable is true.
    try:
        info.config.name
        return True
    except AttributeError:
        log.debug("Skip: %s", info.projectdir)

class Pip:

    env = dict(os.environ, PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')

    def __init__(self, pippath):
        self.pippath = pippath

    def _pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = self.env)

    def installeditable(self, infos):
        specifiers = {}
        for i in infos:
            for req in i.parsedremoterequires():
                s = specifiers.get(req.namepart)
                if s is None:
                    s = req.specifier
                else:
                    log.debug("Intersect %s%s with: %s%s", req.namepart, s, req.namepart, req.specifier)
                    s &= req.specifier
                specifiers[req.namepart] = s
        self._pipinstall(["%s%s" % entry for entry in specifiers.items()])
        self._pipinstall(sum((['-e', i.projectdir] for i in infos), []))

def main_initopt():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    versiontoinfos = {version: set() for version in [sys.version_info.major]}
    home = os.path.expanduser('~')
    def configpaths():
        config = Config.blank()
        config.loadsettings()
        projectsdir = config.projectsdir
        for p in sorted(os.listdir(projectsdir)):
            configpath = os.path.join(projectsdir, p, 'project.arid')
            if os.path.exists(configpath):
                yield configpath
    allinfos = {i.config.name: i for i in (ProjectInfo.seek(os.path.dirname(p)) for p in configpaths()) if _hasname(i)}
    def add(infos, i):
        if i not in infos:
            infos.add(i)
            for p in i.localrequires():
                add(infos, allinfos[p])
    for info in allinfos.values():
        if info.config.executable:
            for pyversion in info.config.pyversions:
                if pyversion in versiontoinfos:
                    add(versiontoinfos[pyversion], info)
    for info in sorted(set().union(*versiontoinfos.values()), key = lambda i: i.projectdir):
        log.debug("Prepare: %s", info.projectdir)
        pipify(info)
    for pyversion, infos in versiontoinfos.items():
        venvpath = os.path.join(home, 'opt', "venv%s" % pyversion)
        pythonname = "python%s" % pyversion
        if not os.path.exists(venvpath):
            subprocess.check_call(['virtualenv', '-p', pythonname, venvpath])
        binpath = os.path.join(venvpath, 'bin')
        Pip(os.path.join(binpath, 'pip')).installeditable(infos)
        magic = ("#!%s" % os.path.join(binpath, pythonname)).encode()
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
