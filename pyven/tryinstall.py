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
from .minivenv import poolsession
from .pipify import pipify
from .projectinfo import ProjectInfo
from .util import bgcontainer, initlogging, pyversiontags
from lagoon import git
from lagoon.program import partial
from urllib.request import urlopen
import logging, xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

def main_tryinstall():
    'Check last release can be installed from PyPI and its tests still pass, for use by CI.'
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
    upstream_devel_packages = list(headinfo.config.upstream.devel.packages)
    for pyversion in reversed(pyversiontags[3]): # XXX: Why only 3?
        log.info("Python version: %s", pyversion)
        with bgcontainer("python:%s" % pyversion) as container:
            containerexec = docker[partial]('exec', container, stdout = None)
            if upstream_devel_packages:
                containerexec('apt-get', 'update')
                containerexec('apt-get', 'install', '-y', *upstream_devel_packages)
            containerexec('pip', 'install', req)
    git.checkout("v%s" % version, stdout = None)
    info = ProjectInfo.seek('.')
    pipify(info)
    with poolsession(True) as openvenv:
        EveryVersion(info, False, False, [], False, openvenv).nose()
