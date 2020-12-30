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

from .minivenv import openvenv
from .projectinfo import ProjectInfo, Req
from .sourceinfo import SourceInfo
from .util import initlogging, TemporaryDirectory
from argparse import ArgumentParser
from itertools import chain
from pkg_resources import resource_filename
import logging, os, subprocess, sys

log = logging.getLogger(__name__)

def pipify(info, version = None):
    release = version is not None
    # Allow release of project without origin:
    description, url = info.descriptionandurl() if release and info.config.github.participant else [None, None]
    config = (-info.config).childctrl()
    config.put('version', scalar = version if release else info.devversion())
    config.put('description', scalar = description)
    config.put('long_description', text = 'long_description()' if release else repr(None))
    config.put('url', scalar = url)
    if not release:
        config.put('author', scalar = None)
    config.put('py_modules', scalar = info.py_modules())
    config.put('install_requires', scalar = info.allrequires() if release else info.remoterequires())
    config.put('scripts', scalar = info.scripts())
    config.put('console_scripts', scalar = info.console_scripts())
    config.put('universal', number = int({2, 3} <= set(info.config.pyversions)))
    # XXX: Use soak to generate these?
    nametoquote = [
        ['setup.py', 'pystr'],
        ['setup.cfg', 'void'],
    ]
    seen = set()
    for name in chain(pyvenbuildrequires(info), info.config.build.requires):
        if name not in seen:
            seen.add(name)
            config.printf("build requires += %s", name)
    if seen != {'setuptools', 'wheel'}:
        nametoquote.append(['pyproject.toml', 'tomlquote'])
    for name, quote in nametoquote:
        config.printf('" = $(%s)', quote)
        config.processtemplate(
                resource_filename(__name__, name + '.aridt'), # TODO LATER: Make aridity get the resource.
                os.path.abspath(os.path.join(info.projectdir, name)))

def pyvenbuildrequires(info):
    yield 'setuptools'
    yield 'wheel'
    reqs = set()
    for p in SourceInfo(info.projectdir).extpaths:
        reqs.update(p.buildrequires())
    for r in sorted(reqs):
        yield r

def main_pipify():
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('-f')
    parser.add_argument('--transient', action = 'store_true')
    parser.add_argument('version', nargs = '?')
    args = parser.parse_args()
    info = ProjectInfo.seek('.') if args.f is None else ProjectInfo('.', args.f)
    pipify(info, args.version)
    setupcommand(info, sys.version_info.major, args.transient, 'egg_info')

def setupcommand(info, pyversion, transient, *command):
    def setup(absexecutable):
        subprocess.check_call([absexecutable, 'setup.py'] + list(command), cwd = info.projectdir)
    buildreqs = list(chain(pyvenbuildrequires(info), info.config.build.requires))
    if {'setuptools', 'wheel'} == set(buildreqs) and sys.version_info.major == pyversion:
        setup(sys.executable)
    else:
        with openvenv(pyversion, buildreqs, transient) as venv:
            setup(venv.programpath('python'))

def installdeps(info, venv, siblings, localrepo):
    with TemporaryDirectory() as workspace:
        editableprojects = {}
        volatileprojects = {}
        pypireqs = []
        def adddeps(i, root):
            for r in i.parsedrequires():
                name = r.namepart
                if name in editableprojects or name in volatileprojects:
                    continue
                if siblings:
                    siblingpath = r.siblingpath(i.contextworkspace())
                    if os.path.exists(siblingpath):
                        editableprojects[name] = j = ProjectInfo.seek(siblingpath)
                        yield j
                        continue
                if localrepo is not None:
                    repopath = os.path.join(localrepo, "%s.git" % name)
                    if os.path.exists(repopath):
                        if siblings:
                            log.warning("Not a sibling, install from repo: %s", name)
                        clonepath = os.path.join(workspace, name)
                        subprocess.check_call(['git', 'clone', '--depth', '1', "file://%s" % repopath, clonepath])
                        volatileprojects[name] = j = ProjectInfo.seek(clonepath)
                        yield j
                        continue
                if root: # Otherwise pip will handle it.
                    pypireqs.append(r.reqstr)
        infos = [info]
        isroot = True
        while infos:
            log.debug("Examine deps of: %s", ', '.join(i.config.name for i in infos))
            nextinfos = []
            for i in infos:
                nextinfos.extend(adddeps(i, isroot))
            infos = nextinfos
            isroot = False
        for i in volatileprojects.values(): # Assume editables already pipified.
            pipify(i)
        pypireqs = list(Req.published(pypireqs))
        venv.install(sum((['-e', i.projectdir] for i in editableprojects.values()), []) + [i.projectdir for i in volatileprojects.values()] + pypireqs)
