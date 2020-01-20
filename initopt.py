#!/usr/bin/env python3

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
from pathlib import Path
from pyvenimpl.pipify import pipify
from pyvenimpl.projectinfo import ProjectInfo
import aridity, logging, subprocess

log = logging.getLogger(__name__)

def main():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    versiontoprojectpaths = {version: [] for version in [3, 2]}
    for configpath in Path.home().glob('projects/*/project.arid'):
        context = aridity.Context()
        with aridity.Repl(context) as repl:
            repl.printf('executable = false')
            repl.printf(". %s", configpath)
        if context.resolved('executable').value:
            projectpath = configpath.parent
            log.debug("Prepare: %s", projectpath)
            pipify(ProjectInfo(projectpath), False)
            for pyversionobj in context.resolved('pyversions'):
                versiontoprojectpaths[pyversionobj.value].append(projectpath)
    for pyversion, projectpaths in versiontoprojectpaths.items():
        venvpath = Path.home() / 'opt' / ("venv%s" % pyversion)
        if not venvpath.exists():
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, venvpath])
        subprocess.check_call([venvpath / 'bin' / 'pip', 'install'] + sum((['-e', p] for p in projectpaths), []))

if '__main__' == __name__:
    main()
