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

import re, os, sys, shutil

def removedir(path):
    if os.path.islink(path):
        os.remove(path)
    else:
        shutil.rmtree(path)

def main():
    roots = sys.argv[1:]
    ignorename = '.hgignore'
    while not os.path.exists(ignorename):
        oldpwd = os.getcwd()
        os.chdir('..')
        if oldpwd == os.getcwd():
            raise Exception(ignorename)
        roots = [os.path.join(os.path.basename(oldpwd), root) for root in roots]
    patterns = []
    with open(ignorename) as f:
        armed = False
        for line in f:
            line, = line.splitlines()
            if armed:
                patterns.append(re.compile(line))
            else:
                armed = '#gclean' == line
    def tryremovepath(path, remove):
        path = os.path.normpath(path)
        for pattern in patterns:
            if pattern.search(path) is not None:
                print >> sys.stderr, path
                remove(path)
                break
    for root in (roots if roots else ['.']):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for name in dirnames:
                tryremovepath(os.path.join(dirpath, name), removedir)
            for name in sorted(filenames):
                tryremovepath(os.path.join(dirpath, name), os.remove)

if '__main__' == __name__:
    main()
