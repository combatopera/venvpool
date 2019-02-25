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

import os, subprocess, pyven, tests
from pyvenimpl import projectinfo, miniconda as mc

class Workspace:

    def __init__(self):
        self.workspace = os.path.dirname(os.getcwd())

    def info(self, projectname):
        return projectinfo.ProjectInfo(os.path.join(self.workspace, projectname))

    def gettransitivedeps(self, info, deps):
        deps.update(info['deps'])
        for project in info['projects']:
            self.gettransitivedeps(self.info(project), deps)

    def checkoutifnecessary(self, info, project):
        if '/' in project:
            return # Assume it's a subdirectory of the context project.
        path = os.path.join(self.workspace, project)
        if not os.path.exists(path): # Allow for diamond dependencies.
            cloneargs = ['-b', info['branch'].get(project, 'master')]
            subprocess.check_call(['git', 'clone'] + cloneargs + ["https://github.com/combatopera/%s.git" % project], cwd = self.workspace)
        info2 = projectinfo.ProjectInfo(path)
        for project2 in info2['projects']:
            self.checkoutifnecessary(info2, project2)

def main():
    workspace = Workspace()
    info = projectinfo.ProjectInfo(os.getcwd())
    for project in info['projects']:
        workspace.checkoutifnecessary(info, project)
    minicondas = [mc.pyversiontominiconda[v] for v in info['pyversions']]
    deps = set()
    workspace.gettransitivedeps(info, deps)
    workspace.gettransitivedeps(workspace.info('pyven'), deps)
    for miniconda in minicondas:
        miniconda.installifnecessary(deps)
    testspath = tests.__file__
    if testspath.endswith('.pyc'):
        testspath = testspath[:-1]
    for miniconda in minicondas:
        # Equivalent to running tests.py directly but with one fewer process launch:
        pyven.Launcher(info, miniconda.pyversion).check_call([testspath])

if '__main__' == __name__:
    main()
