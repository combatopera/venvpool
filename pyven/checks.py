# Copyright 2013, 2014, 2015, 2016, 2017, 2020 Andrzej Cichocki

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
from . import minivenv
from .divcheck import mainimpl as divcheckimpl
from .files import Files
from .projectinfo import ProjectInfo
from .util import Excludes, stderr, stripeol
from itertools import chain
from setuptools import find_packages
import os, re, subprocess, sys

def _licheck(info, workspace, files):
    from .licheck import licheck
    def g():
        excludes = Excludes(info.config.licheck.exclude.globs)
        for path in files.allsrcpaths:
            if os.path.relpath(path, files.root) not in excludes:
                yield path
    _runcheck(licheck, info, list(g()))

def _nlcheck(info, workspace, files):
    from .nlcheck import nlcheck
    _runcheck(nlcheck, files.allsrcpaths)

def _execcheck(info, workspace, files):
    from .execcheck import execcheck
    _runcheck(execcheck, files.pypaths)

def divcheck(info, files):
    divcheckimpl(files.pypaths)

def pyflakes(info, files):
    with open(os.path.join(files.root, '.flakesignore')) as f:
        ignores = [re.compile(stripeol(l)) for l in f]
    prefixlen = len(files.root + os.sep)
    def accept(path):
        for pattern in ignores:
            if pattern.search(path[prefixlen:]) is not None:
                return False
        return True
    paths = [p for p in files.pypaths if accept(p)]
    if paths:
        subprocess.check_call([pathto('pyflakes')] + paths)

def pathto(executable):
    return os.path.join(os.path.dirname(sys.executable), executable)

def _runcheck(check, *args):
    sys.stderr.write("%s: " % check.__name__)
    check(*args)
    stderr('OK')

def main_checks():
    info = ProjectInfo.seek(os.getcwd()) # XXX: Must this be absolute?
    files = Files(info.projectdir)
    for check in divcheck, pyflakes:
        _runcheck(check, info, files)
    status = subprocess.call([
        pathto('nosetests'), '--exe', '-v',
        '--with-xunit', '--xunit-file', files.reportpath,
        '--with-cov', '--cov-report', 'term-missing',
    ] + sum((['--cov', p] for p in chain(find_packages(info.projectdir), info.py_modules())), []) + files.testpaths() + sys.argv[1:])
    reportname = '.coverage'
    if os.path.exists(reportname):
        os.rename(reportname, os.path.join(pathto('..'), reportname)) # XXX: Even when status is non-zero?
    return status

def everyversion(info, workspace, noseargs):
    files = Files(info.projectdir)
    for check in _licheck, _nlcheck, _execcheck:
        check(info, workspace, files)
    for pyversion in info.config.pyversions:
        subprocess.check_call([os.path.abspath(os.path.join(minivenv.bindir(info, workspace, pyversion), 'checks'))] + noseargs, cwd = info.projectdir)

def main_tests():
    info = ProjectInfo.seek('.')
    everyversion(info, info.contextworkspace(), sys.argv[1:])
