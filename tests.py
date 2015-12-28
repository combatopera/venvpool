#!/usr/bin/env runpy

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

import subprocess, sys, os, re

def findfiles(*suffixes):
    for dirpath, dirnames, filenames in os.walk('.'):
        for name in sorted(filenames):
            for suffix in suffixes:
                if name.endswith(suffix):
                    yield os.path.join(dirpath, name)
                    break # Next name.
        dirnames.sort()

bashscript = '''set -e

while ! [[ -e .hg || -e .svn ]]; do cd ..; done

(

    IFS=$'\n'

    for script in licheck nlcheck; do
        $script.py $(
            find '(' -name '*.py' -or -name '*.pyx' -or -name '*.s' -or -name '*.sh' ')' -exec hg st -A '{}' + |
            grep -v '^[IR ]' |
            cut -c 3-
        )
        echo $script: OK >&2
    done

    divcheck.py $(find -name '*.py')
    echo divcheck: OK >&2

    execcheck.py $(find -name '*.py')
    echo execcheck: OK >&2

)
'''

def pyflakes():
    with open('.flakesignore') as f:
        ignores = [re.compile(l.strip()) for l in f]
    paths = []
    for path in findfiles('.py'):
        for pattern in ignores:
            if pattern.search(path) is not None:
                break # Next path.
        else:
            paths.append(path)
    subprocess.check_call(['pyflakes'] + paths)

def main():
    subprocess.check_call(['bash', '-c', bashscript])
    for f in pyflakes,:
        f()
        print >> sys.stderr, "%s: OK" % f.__name__
    sys.exit(subprocess.call(['nosetests', '--exe', '-v']))

if '__main__' == __name__:
    main()
