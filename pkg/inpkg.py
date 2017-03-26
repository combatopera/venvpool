#!/usr/bin/env pyven

import sys
from util import stderr

def main():
    for code in 'sys.path', 'sys.executable', 'sys.argv':
        stderr("%s: %s" % (code, eval(code)))

if '__main__' == __name__:
    main()
