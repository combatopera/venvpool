# Copyright 2013, 2014, 2015, 2016, 2017 Andrzej Cichocki

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

from __future__ import with_statement
from .divcheck import mainimpl as divcheckimpl
from .execcheck import mainimpl as execcheckimpl
from .files import Files
from .licheck import mainimpl as licheckimpl
from .nlcheck import mainimpl as nlcheckimpl
from .projectinfo import ProjectInfo
from .util import stderr, stripeol
import subprocess, sys, os, re

def licheck(info, files):
    def g():
        for path in files.allsrcpaths:
            parentname = os.path.basename(os.path.dirname(path))
            if parentname != 'contrib' and not parentname.endswith('_turbo'):
                yield path
    licheckimpl(info, list(g()))

def nlcheck(info, files):
    nlcheckimpl(files.allsrcpaths)

def divcheck(info, files):
    divcheckimpl(files.pypaths)

def execcheck(info, files):
    execcheckimpl(files.pypaths)

def pyflakes(info, files):
    with open('.flakesignore') as f:
        ignores = [re.compile(stripeol(l)) for l in f]
    def accept(path):
        for pattern in ignores:
            if pattern.search(path) is not None:
                return False
        return True
    paths = [p for p in files.pypaths if accept(p)]
    if paths:
        subprocess.check_call([pathto('pyflakes')] + paths)

def pathto(executable):
    return os.path.join(os.path.dirname(sys.executable), executable)

def main_chekkz():
    while not (os.path.exists('.hg') or os.path.exists('.svn') or os.path.exists('.git')):
        os.chdir('..')
    info = ProjectInfo(os.getcwd())
    files = Files()
    for check in (() if info['proprietary'] else (licheck,)) + (nlcheck, divcheck, execcheck, pyflakes):
        sys.stderr.write("%s: " % check.__name__)
        check(info, files)
        stderr('OK')
    return subprocess.call([pathto('nosetests'), '--exe', '-v', '--with-xunit', '--xunit-file', files.reportpath] + files.testpaths() + sys.argv[1:])
