# Copyright 2013, 2014, 2015, 2016, 2017 Andrzej Cichocki

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

from aridimpl.util import NoSuchPathException
from pyvenimpl.pipify import pipify
from pyvenimpl.projectinfo import ProjectInfo
import logging, os, subprocess, sys

log = logging.getLogger(__name__)

def hasname(info):
    try:
        info['name']
        return True
    except NoSuchPathException:
        pass

def main_initopt():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    versiontoinfos = {version: set() for version in [sys.version_info.major]}
    home = os.path.expanduser('~')
    def configpaths():
        projectsdir = os.path.join(home, 'projects')
        for p in sorted(os.listdir(projectsdir)):
            configpath = os.path.join(projectsdir, p, 'project.arid')
            if os.path.exists(configpath):
                yield configpath
    allinfos = {i['name']: i for i in map(ProjectInfo, configpaths()) if hasname(i)}
    def add(infos, i):
        if i not in infos:
            infos.add(i)
            for p in i['projects']:
                add(infos, allinfos[p])
    for info in allinfos.values():
        if info['executable']:
            for pyversion in info['pyversions']:
                if pyversion in versiontoinfos:
                    add(versiontoinfos[pyversion], info)
    for info in sorted(set().union(*versiontoinfos.values()), key = lambda i: i.projectdir):
        log.debug("Prepare: %s", info.projectdir)
        pipify(info, False)
    for pyversion, infos in versiontoinfos.items():
        venvpath = os.path.join(home, 'opt', "venv%s" % pyversion)
        if not os.path.exists(venvpath):
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, venvpath])
        binpath = os.path.join(venvpath, 'bin')
        subprocess.check_call([os.path.join(binpath, 'pip'), 'install'] + sum((['-e', i.projectdir] for i in infos), []))
        with open(os.path.join(binpath, 'pkg_resources.py'), 'w') as f:
            f.write('''from pkg_resources_lite import load_entry_point
''')
