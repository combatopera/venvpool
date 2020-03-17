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

def endswithifmain(istest, lines):
    if ('    unittest.main()' if istest else '    main()') != lines[-1]:
        return False
    for i in range(len(lines) - 2, -1, -1):
        if '''if '__main__' == __name__:''' == lines[i]:
            return True
        if not lines[i].startswith('    '):
            return False
    return False

def mainimpl(paths): # TODO: Can probably be simplified now that tests are non-executable.
    for path in paths:
        executable = os.stat(path).st_mode & 0x49
        if 0 == executable:
            executable = False
        elif 0x49 == executable:
            executable = True
        else:
            raise Exception(path) # Should be all or nothing.
        basename = os.path.basename(path)
        istest = basename.startswith('test_')
        if basename not in ('tests.py', 'Test.py') and basename.lower().startswith('test') and not istest:
            raise Exception(path) # Catch bad naming. TODO: Also check for duplicate method names.
        if istest and executable:
            raise Exception(path) # All tests should be non-executable.
        with open(path) as f:
            lines = f.read().splitlines()
        hashbang = bool(lines) and lines[0] in (
            '#!/usr/bin/env python',
            '#!/usr/bin/env python3',
        )
        main = bool(lines) and endswithifmain(istest, lines)
        if hashbang and main and executable:
            return
        # An otherwise non-executable file may have a main if it's always passed to an interpreter:
        if (not hashbang) and (not executable):
            return
        raise Exception(path)
