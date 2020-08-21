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

from .initlogging import initlogging
from .projectinfo import ProjectInfo
from argparse import ArgumentParser
import logging

log = logging.getLogger(__name__)
pyversions = '3.8', '3.7', '3.6'

def main_tryinstall():
    from lagoon import docker
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('project')
    config = parser.parse_args()
    if not ProjectInfo.seek('.').config.pypi.participant:
        log.info('Not user-installable.')
        return
    for pyversion in pyversions:
        log.info("Python version: %s", pyversion)
        container = docker.run._d("python:%s" % pyversion, 'sleep', 'inf').rstrip()
        docker('exec', container, 'pip', 'install', config.project, stdout = None)
        docker.rm._f(container, stdout = None)
