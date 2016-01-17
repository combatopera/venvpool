#!/usr/bin/env pyrform

# Copyright 2014 Andrzej Cichocki

# This file is part of pyrform.
#
# pyrform is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyrform is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyrform.  If not, see <http://www.gnu.org/licenses/>.

import subprocess, sys, os, re, licheck as licheckimpl, nlcheck as nlcheckimpl, divcheck as divcheckimpl, execcheck as execcheckimpl

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
    def g():
        for path in filterfiles('.py', '.pyx', '.s', '.sh'):
            if not os.path.basename(os.path.dirname(path)).endswith('_turbo'):
                yield path
    licheckimpl.mainimpl(list(g()))

def nlcheck():
    nlcheckimpl.mainimpl(list(filterfiles('.py', '.pyx', '.s', '.sh')))

def divcheck():
    divcheckimpl.mainimpl(list(findfiles('.py')))

def execcheck():
    execcheckimpl.mainimpl(list(findfiles('.py')))

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
