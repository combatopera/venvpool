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

from tests import Files
import os, subprocess

def isproject():
    for name in '.hg', '.svn', '.git':
        if os.path.exists(name):
            return True

def main():
    while not isproject():
        os.chdir('..')
    agcommand = ['ag', '--noheading', '--nobreak']
    paths = list(Files.findfiles('.py', '.pyx', '.h', '.cpp', '.ui', '.java', '.kt', '.c', '.s', '.sh'))
    ignored = set(subprocess.Popen(['git', 'check-ignore'] + paths, stdout = subprocess.PIPE).communicate()[0].decode().splitlines())
    paths = [p for p in paths if p not in ignored]
    for tag in 'XXX', 'TODO', 'FIXME':
        subprocess.call(agcommand + [tag + ' LATER'] + paths)
        subprocess.call(agcommand + [tag + '(?! LATER)'] + paths)

if '__main__' == __name__:
    main()
