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

import os

execmask = 0x49
magic = '#!'

def execcheck(paths):
    for path in paths:
        basename = os.path.basename(path)
        executable = bool(os.stat(path).st_mode & execmask)
        with open(path) as f:
            hasmagic = f.readline().startswith(magic)
        if basename.lower().startswith('test'):
            if not basename.startswith('test_'):
                raise Exception("Inconsistent name: %s" % path) # Note pyflakes already checks for duplicate method names.
            if executable:
                raise Exception("Should not be executable: %s" % path)
            if hasmagic:
                raise Exception("Using %s is obsolete: %s" % (magic, path))
        else:
            if executable != hasmagic:
                raise Exception(path)
