#!/usr/bin/env python

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

import os, subprocess, pyven, tests
from pyvenimpl import projectinfo, miniconda

def main():
    conf = projectinfo.ProjectInfo(projectinfo.ProjectInfo.infoname).info
    projectdir = os.getcwd()
    os.chdir('..')
    for project in conf['projects']:
        if not os.path.exists(project.replace('/', os.sep)): # Allow a project to depend on a subdirectory of itself.
            subprocess.check_call(['git', 'clone', "https://github.com/combatopera/%s.git" % project])
    os.chdir(projectdir)
    minicondainfos = [miniconda.pyversiontominiconda[v] for v in conf['pyversions']]
    for info in minicondainfos:
        info.installifnecessary(conf['deps'])
    for info in minicondainfos:
        # Equivalent to running tests.py directly but with one fewer process launch:
        pyven.getlauncher(projectdir, conf['projects'], info.pyversion).check_call([tests.__file__])

if '__main__' == __name__:
    main()
