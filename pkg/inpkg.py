#!/usr/bin/env pyven

import sys
from util import stderr

def main():
    stderr("sys.path: %s" % sys.path)
    stderr("sys.executable: %s" % sys.executable)
    stderr("sys.argv: %s" % sys.argv)

if '__main__' == __name__:
    main()
