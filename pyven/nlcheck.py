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
import re

class MoreThanOneEolStyleException(Exception): pass

def nlcheck(paths):
    for path in paths:
        with open(path, 'rb') as f:
            text = f.read().decode()
        eols = set(re.findall(r'\r\n|[\r\n]', text))
        if len(eols) > 1:
            raise MoreThanOneEolStyleException(path)
