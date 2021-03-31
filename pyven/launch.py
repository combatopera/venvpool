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

from .minivenv import poolsession
from .pipify import InstallDeps
from .projectinfo import ProjectInfo
from .util import initlogging
from argparse import ArgumentParser
import subprocess, sys

def main_launch():
    'Run project using a suitable venv from the pool.'
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('--build', action = 'store_true', help = 'rebuild native components')
    args = parser.parse_args()
    info = ProjectInfo.seekany('.')
    _, objref = next(iter(info.console_scripts())).split('=') # XXX: Support more than just the first?
    modulename, qname = objref.split(':')
    with InstallDeps(info, False, None) as installdeps, poolsession(False) as openvenv, openvenv(sys.version_info.major, installdeps) as venv:
        if args.build:
            venv.install(['--no-deps', '-e', info.projectdir])
        status = subprocess.call([venv.programpath('python'), '-c', "from %s import %s; %s()" % (modulename, qname.split('.')[0], qname)])
    sys.exit(status)
