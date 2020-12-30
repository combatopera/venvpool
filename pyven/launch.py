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
from .setuproot import getsetupkwargs
from .util import Path
from contextlib import contextmanager
from pkg_resources import parse_requirements
from tempfile import mkdtemp
import os, subprocess, sys

pooldir = os.path.join(os.path.expanduser('~'), '.pyven', 'pool')

@contextmanager
def _unlockonerror(venv):
    try:
        yield venv
    except:
        venv.unlock()
        raise

@contextmanager
def openvenv(pyversion, requires, transient = False):
    parsedrequires = list(parse_requirements(requires))
    versiondir = os.path.join(pooldir, str(pyversion))
    os.makedirs(versiondir, exist_ok = True)
    for name in [] if transient else sorted(os.listdir(versiondir)):
        venv = Venv(os.path.join(versiondir, name), None)
        if venv.trylock():
            with _unlockonerror(venv):
                if venv.compatible(parsedrequires):
                    break
            venv.unlock()
    else:
        venv = Venv(mkdtemp(dir = versiondir), pyversion)
        with _unlockonerror(venv):
            venv.install(requires)
    try:
        yield venv
    finally:
        venv.delete() if transient else venv.unlock()

def main_launch():
    setuppath = Path.seek('.', 'setup.py')
    setupkwargs = getsetupkwargs(setuppath, ['entry_points', 'install_requires'])
    _, objref = setupkwargs['entry_points']['console_scripts'][0].split('=') # XXX: Support more than just the first?
    modulename, qname = objref.split(':')
    with openvenv(sys.version_info.major, setupkwargs.get('install_requires', [])) as venv:
        venv.install(['--no-deps', '-e', os.path.dirname(setuppath)]) # XXX: Could this be faster?
        sys.exit(subprocess.call([venv.programpath('python'), '-c', "from %s import %s; %s()" % (modulename, qname.split('.')[0], qname)]))
