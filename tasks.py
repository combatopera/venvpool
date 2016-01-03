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

import os, subprocess
from tests import findfiles

def main():
    while not (os.path.exists('.hg') or os.path.exists('.svn')):
        os.chdir('..')
    paths = list(findfiles('.py', '.pyx', '.h', '.cpp', '.ui'))
    for tag in 'XXX', 'TODO', 'FIXME':
        subprocess.call(['pcregrep', '--color=always', tag + ' LATER'] + paths)
        subprocess.call(['pcregrep', '--color=always', tag + '(?! LATER)'] + paths)

if '__main__' == __name__:
    main()
