#!/usr/bin/env pyven

import sys
from util import stderr

def main():
    for code in 'path', 'executable', 'argv':
        stderr("%s: %s" % (name, getattr(sys, name)))

if '__main__' == __name__:
    main()
