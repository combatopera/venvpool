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

from .files import Files
from .minivenv import poolsession
from .pipify import InstallDeps, SimpleInstallDeps
from .projectinfo import ProjectInfo
from .util import bgcontainer, Excludes, initlogging, pyversiontags, stderr
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from aridity.util import NoSuchPathException, openresource
from diapyr.util import singleton
from itertools import chain
from lagoon import diff
from setuptools import find_packages
from tempfile import NamedTemporaryFile
import logging, os, shutil, subprocess, sys

log = logging.getLogger(__name__)
skip = object()

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
    stderr('SKIP' if check(*args) is skip else 'OK')

class EveryVersion:

    def __init__(self, info, siblings, userepo, noseargs, docker, openvenv):
        self.files = Files(info.projectdir)
        self.info = info
        self.siblings = siblings
        self.userepo = userepo
        self.noseargs = noseargs
        self.docker = docker
        self.openvenv = openvenv

    def allchecks(self):
        for check in self.licheck, self.nlcheck, self.execcheck, self.divcheck, self.pyflakes, self.nose, self.readme:
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
            if pyversion >= 3:
                return skip
            subprocess.check_call(["python%s" % pyversion, scriptpath] + self.files.pypaths)
        for pyversion in self.info.config.pyversions:
            _runcheck(pyversion, divcheck)

    def pyflakes(self):
        paths = [path for excludes in [Excludes(self.info.config.flakes.exclude.globs)]
                for path in self.files.pypaths if os.path.relpath(path, self.files.root) not in excludes]
        def pyflakes():
            if paths:
                with self.openvenv(pyversion, SimpleInstallDeps(['pyflakes'])) as venv:
                    subprocess.check_call([venv.programpath('pyflakes')] + paths)
        for pyversion in self.info.config.pyversions:
            _runcheck(pyversion, pyflakes)

    def nose(self):
        upstream_devel_packages = list(self.info.config.upstream.devel.packages)
        with InstallDeps(self.info, self.siblings, _localrepo() if self.userepo else None) as installdeps:
            installdeps.add('nose-cov')
            for pyversion in self.info.config.pyversions:
                reportsdir = os.path.join(self.info.projectdir, 'var', str(pyversion))
                os.makedirs(reportsdir, exist_ok = True)
                xmlpath = os.path.join(reportsdir, 'nosetests.xml')
                if self.docker:
                    coveragepath = os.path.join(self.info.projectdir, '.coverage')
                    with bgcontainer('-v', "%s:%s" % (os.path.abspath(self.info.projectdir), Container.workdir), "python:%s" % pyversiontags[pyversion][0]) as container:
                        container = Container(container)
                        container.inituser()
                        if upstream_devel_packages:
                            for command in ['apt-get', 'update'], ['apt-get', 'install', '-y'] + upstream_devel_packages:
                                container.call(command, check = True, root = True)
                        installdeps(container)
                        cpath = lambda p: os.path.relpath(p, self.info.projectdir).replace(os.sep, '/')
                        status = container.call([
                            'nosetests', '--exe', '-v',
                            '--with-xunit', '--xunit-file', cpath(xmlpath),
                            '--with-cov', '--cov-report', 'term-missing',
                        ] + sum((['--cov', p] for p in chain(find_packages(self.info.projectdir), self.info.py_modules())), []) + [cpath(p) for p in self.files.testpaths(xmlpath)] + self.noseargs)
                else:
                    coveragepath = '.coverage'
                    with self.openvenv(pyversion, installdeps) as venv:
                        status = subprocess.call([
                            venv.programpath('nosetests'), '--exe', '-v',
                            '--with-xunit', '--xunit-file', xmlpath,
                            '--with-cov', '--cov-report', 'term-missing',
                        ] + sum((['--cov', p] for p in chain(find_packages(self.info.projectdir), self.info.py_modules())), []) + self.files.testpaths(xmlpath) + self.noseargs)
                if os.path.exists(coveragepath):
                    shutil.copy2(coveragepath, os.path.join(reportsdir, 'coverage')) # Replace whatever the status, as if we configured the location.
                    os.remove(coveragepath) # Can't simply use rename cross-device in release case.
                assert not status

    def readme(self):
        def first(scope, resolvable):
            for _, o in resolvable.resolve(scope).itero():
                return o
            raise NoSuchPathException('Empty set.')
        def readme():
            if not self.info.config.github.participant:
                return skip
            config = (-self.info.config).childctrl().node
            config.first = first
            config.tagline, _ = self.info.descriptionandurl()
            (-config).execute('commands * name = $label()')
            for mf in sorted(self.info.mainfunctions(), key = lambda mf: mf.name):
                assert mf.doc is not None
                (-config).printf("commands %s doc = %s", mf.name, mf.doc)
            with NamedTemporaryFile('w') as g:
                with openresource(__name__, 'README.md.aridt') as f:
                    (-config).processtemplate(f, g)
                g.flush()
                completed = diff(g.name, os.path.join(self.info.projectdir, 'README.md'), check = False)
                sys.stdout.write(completed.stdout)
                assert completed.returncode in {0, 1}
                assert all('<' != l[0] for l in completed.stdout.splitlines())
        _runcheck('*', readme)

class Container:

    workdir = '/io'

    def __init__(self, container):
        from lagoon import id
        self.uid = int(id._u())
        self.gid = int(id._g())
        self.container = container

    def inituser(self):
        from lagoon import docker
        docker('exec', self.container, 'groupadd', '-g', self.gid, 'pyvengroup', stdout = None)
        docker('exec', self.container, 'useradd', '-g', self.gid, '-u', self.uid, '-m', 'pyvenuser', stdout = None)

    def install(self, args):
        from lagoon import docker
        if args:
            docker('exec', '-w', self.workdir, self.container, 'pip', 'install', *args, stdout = None)

    def call(self, args, check = False, root = False):
        from lagoon import docker
        return docker('exec', '-w', self.workdir, *([] if root else ['-u', "%s:%s" % (self.uid, self.gid)]) + [self.container] + args, stdout = None, check = check)

def main_tests():
    'Run project unit tests and more, also suitable for CI.'
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('--docker', action = 'store_true')
    parser.add_argument('--repo', type = yesno, default = True)
    parser.add_argument('--siblings', type = yesno, default = True)
    parser.add_argument('--transient', action = 'store_true')
    args, noseargs = parser.parse_known_args()
    with poolsession(args.transient) as openvenv:
        EveryVersion(ProjectInfo.seekany('.'), args.siblings, args.repo, noseargs, args.docker, openvenv).allchecks()
