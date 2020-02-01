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

from __future__ import division
from aridimpl.util import NoSuchPathException
from pathlib import Path
from pyvenimpl.pipify import pipify
from pyvenimpl.projectinfo import ProjectInfo
import logging, subprocess

log = logging.getLogger(__name__)

def hasname(info):
    try:
        info['name']
        return True
    except NoSuchPathException:
        pass

def main_initopt():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    versiontoinfos = {version: set() for version in [3, 2]}
    allinfos = {i['name']: i
            for i in (ProjectInfo(configpath) for configpath in Path.home().glob('projects/*/project.arid'))
            if hasname(i)}
    def add(infos, i):
        if i not in infos:
            infos.add(i)
            for p in i['projects']:
                add(infos, allinfos[p])
    for info in allinfos.values():
        if info['executable']:
            for pyversion in info['pyversions']:
                add(versiontoinfos[pyversion], info)
    for info in sorted(set().union(*versiontoinfos.values()), key = lambda i: i.projectdir):
        log.debug("Prepare: %s", info.projectdir)
        pipify(info, False)
    for pyversion, infos in versiontoinfos.items():
        venvpath = Path.home() / 'opt' / ("venv%s" % pyversion)
        if not venvpath.exists():
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, venvpath])
        subprocess.check_call([venvpath / 'bin' / 'pip', 'install'] + sum((['-e', i.projectdir] for i in infos), []))
