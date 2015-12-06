#!/usr/bin/env python

# Copyright 2014 Andrzej Cichocki

# This file is part of runpy.
#
# runpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# runpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with runpy.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, subprocess

workspace = os.path.dirname(os.path.dirname(sys.argv[0]))

def resolveword(word):
    if word.startswith('$'):
        key = word[1:]
        if 'WORKSPACE' == key:
            return workspace
        else:
            return os.environ[key]
    else:
        return word

def resolvepath(path):
    return os.sep.join(resolveword(w) for w in path.split('/'))

def main():
    confname = 'runpy.conf'
    context = os.path.abspath(sys.argv[1])
    while True:
        parent = os.path.dirname(context)
        if parent == context:
            raise Exception(confname)
        context = parent
        confpath = os.path.join(context, confname)
        if os.path.exists(confpath):
            break
    conf = {}
    execfile(confpath, conf)
    os.environ['PATH'] = os.pathsep.join([resolvepath(p) for p in conf['path']] + [os.environ['PATH']])
    os.environ['PYTHONPATH'] = os.pathsep.join(resolvepath(p) for p in conf['pythonpath'])
    subprocess.check_call(['python'] + sys.argv[1:])

if '__main__' == __name__:
    main()
