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

import sys, os

def main():
    for path in sys.argv[1:]:
        executable = os.stat(path).st_mode & 0x49
        if 0 == executable:
            executable = False
        elif 0x49 == executable:
            executable = True
        else:
            raise Exception(path) # Should be all or nothing.
        basename = os.path.basename(path)
        istest = basename.startswith('test_')
        if basename.lower().startswith('test') and not istest:
            raise Exception(path) # Catch bad naming.
        if istest and not executable:
            raise Exception(path) # All tests should be executable.
        f = open(path)
        try:
            lines = f.read().splitlines()
        finally:
            f.close()
        hashbang = lines[0] in ('#!/usr/bin/env python', '#!/usr/bin/env runpy')
        main = lines[-2:] == ['''if '__main__' == __name__:''', '    unittest.main()' if istest else '    main()']
        if 1 != len(set([hashbang, main, executable])):
            raise Exception(path) # Want all or nothing.

if '__main__' == __name__:
    main()
