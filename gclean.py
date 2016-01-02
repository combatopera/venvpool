#!/usr/bin/env python

import re, os, sys

def main():
    ignorename = '.hgignore'
    while not os.path.exists(ignorename):
        oldpwd = os.getcwd()
        os.chdir('..')
        if oldpwd == os.getcwd():
            raise Exception(ignorename)
    patterns = []
    with open(ignorename) as f:
        for line in f:
            line, = line.splitlines()
            patterns.append(re.compile(line))
    root = '.'
    for dirpath, dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            path = path[len(root + os.sep):]
            for pattern in patterns:
                if pattern.search(path) is not None:
                    print >> sys.stderr, path
                    os.remove(path)
                    break
        dirnames.sort()

if '__main__' == __name__:
    main()
