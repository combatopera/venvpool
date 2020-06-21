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
from argparse import ArgumentParser
import subprocess

def main_tasks():
    parser = ArgumentParser()
    parser.add_argument('-q', action = 'count', default = 0)
    config = parser.parse_args()
    root, = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().splitlines()
    agcommand = ['ag', '--noheading', '--nobreak']
    # XXX: Integrate with declared project resource types?
    paths = list(Files.relpaths(root, ['.py', '.pyx', '.h', '.cpp', '.ui', '.java', '.kt', '.c', '.s', '.sh', '.arid', '.aridt', '.gradle', '.java', '.mk'], ['Dockerfile', 'Makefile']))
    for tag in ['xxx', 'todo', 'fixme'][config.q:]:
        tag = tag.upper()
        subprocess.call(agcommand + [tag + ' LATER'] + paths, cwd = root)
        subprocess.call(agcommand + [tag + '(?! LATER)'] + paths, cwd = root)
