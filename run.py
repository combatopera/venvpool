#!/usr/bin/env python

# Copyright 2014 Andrzej Cichocki

# This file is part of pyrform.
#
# pyrform is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyrform is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyrform.  If not, see <http://www.gnu.org/licenses/>.

import os, sys

workspace = os.path.dirname(os.path.dirname(sys.argv[0]))

def prepend(paths, envkey):
    current = [os.environ[envkey]] if envkey in os.environ else []
    os.environ[envkey] = os.pathsep.join(paths + current)

def main():
    confname = 'project.info'
    context = os.getcwd()
    while True:
        confpath = os.path.join(context, confname)
        if os.path.exists(confpath):
            break
        parent = os.path.dirname(context)
        if parent == context:
            raise Exception(confname)
        context = parent
    conf = {}
    execfile(confpath, conf)
    prepend([os.path.join(os.environ['MINICONDA_HOME'], 'bin')], 'PATH')
    # XXX: Also add absolute path of context project so manually-executed tests can find e.g. turboconf?
    prepend([os.path.join(workspace, project.replace('/', os.sep)) for project in conf['projects']], 'PYTHONPATH')
    os.execvp('python', ['python'] + sys.argv[1:])

if '__main__' == __name__:
    main()
