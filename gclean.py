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

import re, os, sys

def main():
    ignorename = '.hgignore'
    while not os.path.exists(ignorename):
        oldpwd = os.getcwd()
        os.chdir('..')
        if oldpwd == os.getcwd():
            raise Exception(ignorename)
    patterns = []
    with open(ignorename) as f:
        for line in f:
            line, = line.splitlines()
            patterns.append(re.compile(line))
    root = '.'
    for dirpath, dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            path = path[len(root + os.sep):]
            for pattern in patterns:
                if pattern.search(path) is not None:
                    print >> sys.stderr, path
                    os.remove(path)
                    break
        dirnames.sort()

if '__main__' == __name__:
    main()
