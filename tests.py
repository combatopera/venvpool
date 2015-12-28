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

IFS=$'\n'

for script in licheck; do
    $script.py $(
        find '(' -name '*.py' -or -name '*.pyx' -or -name '*.s' -or -name '*.sh' ')' -exec hg st -A '{}' + |
        grep -v '^[IR ]' |
        cut -c 3-
    )
    echo $script: OK >&2
done
'''

def nlcheck():
    command = ['nlcheck.py']
    badstatuses = set('IR ')
    for line in subprocess.Popen(['hg', 'st', '-A'] + list(findfiles('.py', '.pyx', '.s', '.sh')), stdout = subprocess.PIPE).stdout:
        line, = line.splitlines()
        if line[0] not in badstatuses:
            command.append(line[2:])
    subprocess.check_call(command)

def divcheck():
    subprocess.check_call(['divcheck.py'] + list(findfiles('.py')))

def execcheck():
    subprocess.check_call(['execcheck.py'] + list(findfiles('.py')))

def pyflakes():
    with open('.flakesignore') as f:
        ignores = [re.compile(l.strip()) for l in f]
    command = ['pyflakes']
    for path in findfiles('.py'):
        for pattern in ignores:
            if pattern.search(path) is not None:
                break # Next path.
        else:
            command.append(path)
    subprocess.check_call(command)

def main():
    while not (os.path.exists('.hg') or os.path.exists('.svn')):
        os.chdir('..')
    subprocess.check_call(['bash', '-c', bashscript])
    for f in nlcheck, divcheck, execcheck, pyflakes:
        f()
        print >> sys.stderr, "%s: OK" % f.__name__
    sys.exit(subprocess.call(['nosetests', '--exe', '-v']))

if '__main__' == __name__:
    main()
