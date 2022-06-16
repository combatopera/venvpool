# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022 Andrzej Cichocki

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

from .pipify import InstallDeps
from .projectinfo import ProjectInfo
from argparse import ArgumentParser
from venvpool import initlogging, Pool
import subprocess, sys

def main_launch(): # TODO: Retire in favour of venvpool module.
    'Run project using a suitable venv from the pool.'
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('--build', action = 'store_true', help = 'rebuild native components')
    args = parser.parse_args()
    info = ProjectInfo.seekany('.')
    _, objref = next(iter(info.console_scripts())).split('=') # XXX: Support more than just the first?
    modulename, qname = objref.split(':')
    with InstallDeps(info, False, None) as installdeps, Pool(sys.version_info.major).readonlyorreadwrite[args.build](installdeps) as venv:
        if args.build:
            venv.install(['--no-deps', '-e', info.projectdir]) # XXX: Can this be done without venv install?
        status = subprocess.call([venv.programpath('python'), '-c', "from %s import %s; %s()" % (modulename, qname.split('.')[0], qname)])
    sys.exit(status)
