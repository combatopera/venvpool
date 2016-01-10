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

import os, re, subprocess

def pattern(*patterns):
    return re.compile("^(?:%s)$" % '|'.join(patterns))

projectsdir = os.path.join(os.path.expanduser('~'), 'projects')
publicspecs = pattern('pym2149', 'pym2149-wiki', 'pyrbo', 'runpy', 'diapyr', 'aridipy')
privatespecs = pattern('songs/[^/]+', 'lists', 'sounds', 'www')

def main():
    projectdir = os.getcwd()
    if not projectdir.startswith(projectsdir):
        raise Exception(projectdir)
    reldir = projectdir[len(projectsdir + os.sep):]
    spec = reldir.replace(os.sep, '/')
    public = publicspecs.search(spec) is not None
    if public:
        with open(os.path.join(os.path.dirname(__file__), 'bitbucket.secret')) as f:
            password, = f.read().splitlines()
        urlformat = 'https://combatopera:%s@bitbucket.org/combatopera/' + spec.replace('-', '/')
        subprocess.check_call(['hg', 'push', urlformat % password])
    if public or privatespecs.search(spec) is not None:
        for drive in 'Buffalo', 'Seagate', 'WD':
            path = "/mnt/%s/arc/clones/%s-clone" % (drive, reldir)
            subprocess.check_call(['hg', 'push', path])

if '__main__' == __name__:
    main()
