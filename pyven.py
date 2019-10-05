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

from pyvenimpl import projectinfo, miniconda
from warnings import warn
import os, sys, subprocess, itertools, aridity

class WrongBranchException(Exception): pass

def branchornone(projectpath):
    if os.path.exists(os.path.join(projectpath, '.git')):
        process = subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd = projectpath, stdout = subprocess.PIPE)
        lines = process.communicate()[0].decode().splitlines()
        if process.wait():
            raise Exception
        branch, = lines
        return branch
    infopath = os.path.join(projectpath, '.pyven.arid')
    if os.path.exists(infopath):
        context = aridity.Context()
        with aridity.Repl(context) as repl:
            repl.printf(". %s", infopath)
        return context.resolved('branch').value

class Launcher:

    @classmethod
    def projectpaths(cls, workspace, info, seenpaths):
        for project in info['projects']:
            path = os.path.join(workspace, project.replace('/', os.sep))
            if path in seenpaths:
                continue
            expectedbranch = info['branch'].get(project, 'master')
            actualbranch = branchornone(os.path.join(workspace, project.split('/', 1)[0]))
            if actualbranch is None:
                warn("Unknown branch: %s" % path)
            elif actualbranch != expectedbranch:
                raise WrongBranchException("For %s expected %s but branch is: %s" % (project, expectedbranch, actualbranch))
            seenpaths.add(path)
            yield path
            if '/' in project:
                continue
            info2 = projectinfo.ProjectInfo(path)
            for path2 in cls.projectpaths(workspace, info2, seenpaths):
                yield path2

    @staticmethod
    def getenv(projectpaths):
        key = 'PYTHONPATH'
        env = os.environ.copy()
        try:
            currentpaths = [env[key]] # No need to actually split.
        except KeyError:
            currentpaths = []
        env[key] = os.pathsep.join(itertools.chain(projectpaths, currentpaths))
        return env

    def __init__(self, info, pyversion):
        workspace = os.path.dirname(info.projectdir)
        self.env = self.getenv(self.projectpaths(workspace, info, set()))
        self.pathtopython = miniconda.pyversiontominiconda[pyversion].executable()

    def replace(self, args):
        os.execvpe(self.pathtopython, [self.pathtopython] + args, self.env)

    def check_call(self, args):
        subprocess.check_call([self.pathtopython] + args, env = self.env)

def main():
    try:
        info = projectinfo.ProjectInfo(os.path.dirname(os.path.realpath(sys.argv[1])))
    except projectinfo.ProjectInfoNotFoundException:
        os.execvp(sys.executable, [sys.executable] + sys.argv[1:])
    Launcher(info, info['pyversions'][0]).replace(sys.argv[1:])

if '__main__' == __name__:
    main()
