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

import sys, re

def main():
    for path in sys.argv[1:]:
        with open(path, 'rb') as f:
            text = f.read()
        eols = set(re.findall(r'\r\n|[\r\n]', text))
        if len(eols) > 1:
            raise Exception(path)

if '__main__' == __name__:
    main()
