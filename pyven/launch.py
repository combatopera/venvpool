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
from .pipify import SimpleInstallDeps
from .setuproot import getsetupkwargs
from .util import Path
import os, subprocess, sys

def main_launch():
    setuppath = Path.seek('.', 'setup.py')
    setupkwargs = getsetupkwargs(setuppath, ['entry_points', 'install_requires'])
    _, objref = setupkwargs['entry_points']['console_scripts'][0].split('=') # XXX: Support more than just the first?
    modulename, qname = objref.split(':')
    with openvenv(sys.version_info.major, SimpleInstallDeps(setupkwargs.get('install_requires', []))) as venv:
        venv.install(['--no-deps', '-e', os.path.dirname(setuppath)]) # XXX: Could this be faster?
        sys.exit(subprocess.call([venv.programpath('python'), '-c', "from %s import %s; %s()" % (modulename, qname.split('.')[0], qname)]))
