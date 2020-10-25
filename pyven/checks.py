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
from .projectinfo import ProjectInfo, ProjectInfoNotFoundException
from .setuproot import setuptools as fakesetuptools
from .util import Excludes, initlogging, Path, stderr
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from aridity.util import openresource
from diapyr.util import singleton
from itertools import chain
from setuptools import find_packages
import logging, os, shutil, subprocess, sys

log = logging.getLogger(__name__)

@singleton
class yesno:

    d = dict(no = False, yes = True)

    def __call__(self, s):
        return self.d[s]

def _localrepo():
    config = ConfigCtrl()
    config.loadsettings()
    return config.node.buildbot.repo

def _runcheck(variant, check, *args):
    sys.stderr.write("%s[%s]: " % (check.__name__, variant))
    sys.stderr.flush()
    check(*args)
    stderr('OK')

class EveryVersion:

    def __init__(self, info, siblings, userepo, noseargs):
        self.files = Files(info.projectdir)
        self.info = info
        self.siblings = siblings
        self.userepo = userepo
        self.noseargs = noseargs

    def allchecks(self):
        for check in self.licheck, self.nlcheck, self.execcheck, self.divcheck, self.pyflakes, self.nose:
            check()

    def licheck(self):
        from .licheck import licheck
        def g():
            excludes = Excludes(self.info.config.licheck.exclude.globs)
            for path in self.files.allsrcpaths:
                if os.path.relpath(path, self.files.root) not in excludes:
                    yield path
        _runcheck('*', licheck, self.info, list(g()))

    def nlcheck(self):
        from .nlcheck import nlcheck
        _runcheck('*', nlcheck, self.files.allsrcpaths)

    def execcheck(self):
        from .execcheck import execcheck
        _runcheck('*', execcheck, self.files.pypaths)

    def divcheck(self):
        from . import divcheck
        scriptpath = divcheck.__file__
        def divcheck():
            if pyversion < 3:
                subprocess.check_call([Venv(self.info, pyversion).programpath('python'), scriptpath] + self.files.pypaths)
            else:
                sys.stderr.write('SKIP ')
        for pyversion in self.info.config.pyversions:
            _runcheck(pyversion, divcheck)

    def pyflakes(self):
        paths = [path for excludes in [Excludes(self.info.config.flakes.exclude.globs)]
                for path in self.files.pypaths if os.path.relpath(path, self.files.root) not in excludes]
        def pyflakes():
            if paths:
                venv = Venv(self.info, pyversion)
                pyflakesexe = venv.programpath('pyflakes')
                if not os.path.exists(pyflakesexe):
                    venv.install(['pyflakes'])
                subprocess.check_call([pyflakesexe] + paths)
        for pyversion in self.info.config.pyversions:
            _runcheck(pyversion, pyflakes)

    def nose(self):
        for pyversion in self.info.config.pyversions:
            venv = Venv(self.info, pyversion)
            nosetests = venv.programpath('nosetests')
            if not os.path.exists(nosetests):
                self.info.installdeps(venv, self.siblings, _localrepo() if self.userepo else None)
                venv.install(['nose-cov'])
            # XXX: Doesn't pyximport take care of this?
            subprocess.check_call([os.path.abspath(venv.programpath('python')), 'setup.py', 'build_ext', '--inplace'], cwd = self.info.projectdir)
            reportpath = os.path.join(venv.venvpath, 'nosetests.xml')
            status = subprocess.call([
                nosetests, '--exe', '-v',
                '--with-xunit', '--xunit-file', reportpath,
                '--with-cov', '--cov-report', 'term-missing',
            ] + sum((['--cov', p] for p in chain(find_packages(self.info.projectdir), self.info.py_modules())), []) + self.files.testpaths(reportpath) + self.noseargs)
            reportname = '.coverage'
            if os.path.exists(reportname):
                shutil.copy2(reportname, venv.venvpath) # XXX: Even when status is non-zero?
                os.remove(reportname)
            assert not status

def main_tests():
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('--siblings', type = yesno, default = True)
    parser.add_argument('--repo', type = yesno, default = True)
    config, noseargs = parser.parse_known_args()
    try:
        info = ProjectInfo.seek('.')
    except ProjectInfoNotFoundException:
        setuppath = Path.seek('.', 'setup.py')
        if setuppath is None:
            raise
        log.info('Use setuptools mode.')
        with openresource(__name__, 'setuptools.arid') as f:
            info = ProjectInfo(setuppath.parent, f)
        setupkwargs = eval(subprocess.check_output([sys.executable, fakesetuptools.__file__, setuppath]))
        (-info.config).printf("name = %s", setupkwargs['name'])
        for r in setupkwargs['install_requires']:
            (-info.config).printf("requires += %s", r)
    EveryVersion(info, config.siblings, config.repo, noseargs).allchecks()
