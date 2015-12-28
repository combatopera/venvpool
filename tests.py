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

def stripeol(line):
    line, = line.splitlines()
    return line

def findfiles(*suffixes):
    for dirpath, dirnames, filenames in os.walk('.'):
        for name in sorted(filenames):
            for suffix in suffixes:
                if name.endswith(suffix):
                    yield os.path.join(dirpath, name)
                    break # Next name.
        dirnames.sort()

def filterfiles(*suffixes):
    badstatuses = set('IR ')
    for line in subprocess.Popen(['hg', 'st', '-A'] + list(findfiles(*suffixes)), stdout = subprocess.PIPE).stdout:
        line = stripeol(line)
        if line[0] not in badstatuses:
            yield line[2:]

def licheck():
    subprocess.check_call(['licheck.py'] + list(filterfiles('.py', '.pyx', '.s', '.sh')))

def nlcheck():
    subprocess.check_call(['nlcheck.py'] + list(filterfiles('.py', '.pyx', '.s', '.sh')))

def divcheck():
    subprocess.check_call(['divcheck.py'] + list(findfiles('.py')))

def execcheck():
    subprocess.check_call(['execcheck.py'] + list(findfiles('.py')))

def pyflakes():
    with open('.flakesignore') as f:
        ignores = [re.compile(stripeol(l)) for l in f]
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
    for f in licheck, nlcheck, divcheck, execcheck, pyflakes:
        f()
        print >> sys.stderr, "%s: OK" % f.__name__
    sys.exit(subprocess.call(['nosetests', '--exe', '-v']))

if '__main__' == __name__:
    main()
