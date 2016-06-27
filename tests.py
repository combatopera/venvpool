#!/usr/bin/env pyven

# Copyright 2013, 2014, 2015, 2016 Andrzej Cichocki

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

import subprocess, sys, os, re, licheck as licheckimpl, nlcheck as nlcheckimpl, divcheck as divcheckimpl, execcheck as execcheckimpl

def stripeol(line):
    line, = line.splitlines()
    return line

class Files:

    @staticmethod
    def findfiles(*suffixes):
        for dirpath, dirnames, filenames in os.walk('.'):
            for name in sorted(filenames):
                for suffix in suffixes:
                    if name.endswith(suffix):
                        yield os.path.join(dirpath, name)
                        break # Next name.
            dirnames.sort()

    @classmethod
    def filterfiles(cls, *suffixes):
        badstatuses = set('IR ')
        for line in subprocess.Popen(['hg', 'st', '-A'] + list(cls.findfiles(*suffixes)), stdout = subprocess.PIPE).stdout:
            line = stripeol(line)
            if line[0] not in badstatuses:
                yield line[2:]

    def __init__(self):
        self.allsrcpaths = list(self.filterfiles('.py', '.pyx', '.s', '.sh', '.h', '.cpp', '.cxx'))
        self.pypaths = [p for p in self.allsrcpaths if p.endswith('.py')]

def licheck(files):
    def g():
        for path in files.allsrcpaths:
            if not os.path.basename(os.path.dirname(path)).endswith('_turbo'):
                yield path
    licheckimpl.mainimpl(list(g()))

def nlcheck(files):
    nlcheckimpl.mainimpl(files.allsrcpaths)

def divcheck(files):
    divcheckimpl.mainimpl(files.pypaths)

def execcheck(files):
    execcheckimpl.mainimpl(files.pypaths)

def pyflakes(files):
    with open('.flakesignore') as f:
        ignores = [re.compile(stripeol(l)) for l in f]
    def accept(path):
        for pattern in ignores:
            if pattern.search(path) is not None:
                return False
        return True
    paths = [p for p in files.pypaths if accept(p)]
    if paths:
        subprocess.check_call(['pyflakes'] + paths)

def main():
    while not (os.path.exists('.hg') or os.path.exists('.svn')):
        os.chdir('..')
    files = Files()
    for check in licheck, nlcheck, divcheck, execcheck, pyflakes:
        check(files)
        print >> sys.stderr, "%s: OK" % check.__name__
    sys.exit(subprocess.call(['nosetests', '--exe', '-v', '-m', '^test_']))

if '__main__' == __name__:
    main()
