# Copyright 2013, 2014, 2015, 2016, 2017, 2020 Andrzej Cichocki

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

from __future__ import with_statement
import os

def mainimpl(paths): # TODO: Can probably be simplified now that tests are non-executable.
    for path in paths:
        if os.stat(path).st_mode & 0x49:
            raise Exception("Should not be executable: %s" % path)
        basename = os.path.basename(path)
        istest = basename.startswith('test_')
        if basename not in ('tests.py', 'Test.py') and basename.lower().startswith('test') and not istest:
            raise Exception(path) # Catch bad naming. Note pyflakes already checks for duplicate method names.
        with open(path) as f:
            magic = '#!'
            if f.readline().startswith(magic):
                raise Exception("Using %s is obsolete: %s" % (magic, path))
