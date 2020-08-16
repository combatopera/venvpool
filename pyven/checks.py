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
from .files import Files
from .minivenv import Venv
from .projectinfo import ProjectInfo
from .util import Excludes, stderr, stripeol
from argparse import ArgumentParser
from aridity.config import Config
from itertools import chain
from setuptools import find_packages
import os, re, subprocess, sys

def _licheck(info, noseargs, files):
    from .licheck import licheck
    def g():
        excludes = Excludes(info.config.licheck.exclude.globs)
        for path in files.allsrcpaths:
            if os.path.relpath(path, files.root) not in excludes:
                yield path
    _runcheck('*', licheck, info, list(g()))

def _nlcheck(info, noseargs, files):
    from .nlcheck import nlcheck
    _runcheck('*', nlcheck, files.allsrcpaths)

def _execcheck(info, noseargs, files):
    from .execcheck import execcheck
    _runcheck('*', execcheck, files.pypaths)

def _divcheck(info, noseargs, files):
    from . import divcheck
    scriptpath = divcheck.__file__
    def divcheck():
        if pyversion < 3:
            subprocess.check_call([Venv(info, pyversion).programpath('python'), scriptpath] + files.pypaths)
        else:
            sys.stderr.write('SKIP ')
    for pyversion in info.config.pyversions:
        _runcheck(pyversion, divcheck)

def _pyflakes(info, noseargs, files):
    with open(os.path.join(files.root, '.flakesignore')) as f:
        ignores = [re.compile(stripeol(l)) for l in f]
    prefixlen = len(files.root + os.sep)
    def accept(path):
        for pattern in ignores:
            if pattern.search(path[prefixlen:]) is not None:
                return False
        return True
    paths = [p for p in files.pypaths if accept(p)]
    def pyflakes():
        if paths:
            venv = Venv(info, pyversion)
            pyflakesexe = venv.programpath('pyflakes')
            if not os.path.exists(pyflakesexe):
                venv.install(['pyflakes'])
            subprocess.check_call([pyflakesexe] + paths)
    for pyversion in info.config.pyversions:
        _runcheck(pyversion, pyflakes)

def _nose(info, noseargs, files):
    parser = ArgumentParser()
    parser.add_argument('--heads', action = 'store_true') # TODO: Dedicated buildbot entrypoint.
    config, noseargs = parser.parse_known_args(noseargs)
    for pyversion in info.config.pyversions:
        venv = Venv(info, pyversion)
        nosetests = venv.programpath('nosetests')
        if not os.path.exists(nosetests):
            info.installdeps(venv, _localrepo() if config.heads else None)
            venv.install(['nose-cov'])
        reportpath = os.path.join(venv.venvpath, 'nosetests.xml')
        status = subprocess.call([
            nosetests, '--exe', '-v',
            '--with-xunit', '--xunit-file', reportpath,
            '--with-cov', '--cov-report', 'term-missing',
        ] + sum((['--cov', p] for p in chain(find_packages(info.projectdir), info.py_modules())), []) + files.testpaths(reportpath) + noseargs)
        reportname = '.coverage'
        if os.path.exists(reportname):
            os.rename(reportname, os.path.join(venv.venvpath, reportname)) # XXX: Even when status is non-zero?
        assert not status

def _localrepo():
    config = Config.blank()
    config.loadsettings()
    return config.buildbot.repo

def _runcheck(variant, check, *args):
    sys.stderr.write("%s[%s]: " % (check.__name__, variant))
    sys.stderr.flush()
    check(*args)
    stderr('OK')

def everyversion(info, noseargs):
    files = Files(info.projectdir)
    for check in _licheck, _nlcheck, _execcheck, _divcheck, _pyflakes, _nose:
        check(info, noseargs, files)

def main_tests():
    everyversion(ProjectInfo.seek('.'), sys.argv[1:])
