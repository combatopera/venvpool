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

from .checks import EveryVersion
from .pipify import pipify
from .projectinfo import ProjectInfo
from .util import initlogging
from contextlib import contextmanager
from lagoon import git
from urllib.request import urlopen
import logging, xml.etree.ElementTree as ET

log = logging.getLogger(__name__)
pyversions = '3.8', '3.7', '3.6'

@contextmanager
def bgcontainer(*dockerrunargs):
    from lagoon import docker
    container = docker.run._d(*dockerrunargs + ('sleep', 'inf')).rstrip()
    try:
        yield container
    finally:
        docker.rm._f(container, stdout = None)

def main_tryinstall():
    from lagoon import docker
    initlogging()
    headinfo = ProjectInfo.seek('.')
    if not headinfo.config.pypi.participant: # XXX: Or look for tags?
        log.info('Not user-installable.')
        return
    project = headinfo.config.name
    # XXX: When building a tag use that same version?
    with urlopen("https://pypi.org/rss/project/%s/releases.xml" % project) as f:
        version = ET.parse(f).find('./channel/item/title').text
    req = "%s==%s" % (project, version)
    for pyversion in pyversions:
        log.info("Python version: %s", pyversion)
        with bgcontainer("python:%s" % pyversion) as container:
            docker('exec', container, 'pip', 'install', req, stdout = None)
    git.checkout("v%s" % version, stdout = None)
    info = ProjectInfo.seek('.')
    pipify(info)
    EveryVersion(info, False, False, []).allchecks()
