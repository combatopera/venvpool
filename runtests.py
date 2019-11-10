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

from pyvenimpl import projectinfo, miniconda as mc
import os, pyven, tests, sys

def main():
    info = projectinfo.ProjectInfo(os.getcwd())
    minicondas = [mc.pyversiontominiconda[v] for v in info['pyversions']]
    testspath = tests.__file__
    if testspath.endswith('.pyc'):
        testspath = testspath[:-1]
    for miniconda in minicondas:
        # Equivalent to running tests.py directly but with one fewer process launch:
        pyven.Launcher(info, miniconda.pyversion).check_call([testspath] + sys.argv[1:])

if '__main__' == __name__:
    main()
