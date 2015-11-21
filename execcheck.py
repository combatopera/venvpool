#!/usr/bin/env python

import sys, re, os

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
