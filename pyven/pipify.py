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

from .minivenv import Venv
from .projectinfo import ProjectInfo
from .sourceinfo import SourceInfo
from argparse import ArgumentParser
from itertools import chain
from pkg_resources import resource_filename
import os, subprocess, sys

def _devversion(info):
    releases = [int(t[1:]) for t in subprocess.check_output(['git', 'tag'], cwd = info.projectdir, universal_newlines = True).splitlines() if 'v' == t[0]]
    return "%s.dev0" % ((max(releases) if releases else 0) + 1)

def pipify(info, version = None):
    release = version is not None
    # Allow release of project without origin:
    description, url = info.descriptionandurl() if release and info.config.github.participant else [None, None]
    config = (-info.config).createchild()
    config.put('version', scalar = version if release else _devversion(info))
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
    parser = ArgumentParser()
    parser.add_argument('-f')
    config = parser.parse_args()
    info = ProjectInfo.seek('.') if config.f is None else ProjectInfo('.', config.f)
    pipify(info)
    buildreqs = list(chain(pyvenbuildrequires(info), info.config.build.requires))
    if {'setuptools', 'wheel'} == set(buildreqs):
        executable = sys.executable
    else:
        venv = Venv(info, sys.version_info.major, 'build')
        venv.install(buildreqs)
        executable = venv.programpath('python')
    subprocess.check_call([executable, 'setup.py', 'egg_info'], cwd = info.projectdir)
