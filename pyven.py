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

import os, sys, subprocess, itertools
from pyvenimpl import licheck, miniconda

def getenv(projectpaths):
    key = 'PYTHONPATH'
    env = os.environ.copy()
    try:
        currentpaths = [env[key]] # No need to actually split.
    except KeyError:
        currentpaths = []
    env[key] = os.pathsep.join(itertools.chain(projectpaths, currentpaths))
    return env

def main():
    context = os.path.dirname(os.path.realpath(sys.argv[1]))
    while True:
        confpath = os.path.join(context, licheck.infoname)
        if os.path.exists(confpath):
            break
        parent = os.path.dirname(context)
        if parent == context:
            raise Exception(licheck.infoname)
        context = parent
    conf = licheck.loadprojectinfo(confpath)
    pyversion = conf['pyversions'][0]
    mainimpl(context, conf, pyversion, sys.argv[1:], True)

def mainimpl(projectdir, conf, pyversion, pythonargs, replace):
    pathtopython = os.path.join(miniconda.pyversiontominiconda[pyversion].home(), 'bin', 'python')
    workspace = os.path.dirname(projectdir)
    env = getenv(os.path.join(workspace, project.replace('/', os.sep)) for project in conf['projects'])
    if replace:
        os.execvpe(pathtopython, [pathtopython] + pythonargs, env)
    else:
        subprocess.check_call([pathtopython] + pythonargs, env = env)

if '__main__' == __name__:
    main()
