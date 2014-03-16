#!/usr/bin/env python

import os, subprocess, sys, re

def main():
    top = '.'
    flakesregex = []
    f = open(os.path.join(top, '.flakesignore'))
    try:
      for line in f:
        line, = line.splitlines()
        flakesregex.append(line)
    finally:
      f.close()
    if flakesregex:
      flakesregex = re.compile('|'.join(flakesregex))
      def flakesaccept(path):
        return flakesregex.search(path[len(top) + len(os.sep):].replace(os.sep, '/')) is None
    else:
      flakesaccept = lambda path: True
    paths = []
    for dirpath, dirnames, filenames in os.walk(top):
      paths.extend(sorted(os.path.join(dirpath, n) for n in filenames if n.endswith('.py')))
      dirnames.sort()
    sys.exit(subprocess.call(['pyflakes'] + [p for p in paths if flakesaccept(p)]))

if __name__ == '__main__':
  main()
