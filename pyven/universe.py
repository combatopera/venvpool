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

from concurrent.futures import ThreadPoolExecutor
from diapyr.util import innerclass
from pkg_resources import parse_version
from splut import invokeall
from urllib.request import urlopen
import json, logging

log = logging.getLogger(__name__)

class Universe:

    class PypiProject:

        def __init__(self, releases):
            releases = [str(r) for r in sorted(map(parse_version, releases))]
            # self.cudfversiontorelease = {1 + i: r for i, r in enumerate(releases)}
            self.releasetocudfversion = {r: 1 + i for i, r in enumerate(releases)}
            self.devcudfversion = len(releases) + 1

    @innerclass
    class EditableProject:

        releasetocudfversion = {}
        cudfversions = 1,

        def __init__(self, info):
            self.info = info

        def cudfdepends(self, cudfversion):
            reqs = self.info.parsedremoterequires()
            self._update(r.namepart for r in reqs)
            def cudfdepend(r):
                p = self.projects[r.namepart]
                bounds = ["%s %s %s" % (r.namepart, '=' if '==' == s.operator else s.operator, p.releasetocudfversion[s.version]) for s in r.specifier]
                return ', '.join(bounds) if bounds else r.namepart
            return [cudfdepend(r) for r in reqs]

    def __init__(self, editableinfos):
        self.projects = {i.config.name: self.EditableProject(i) for i in editableinfos}

    def _update(self, names):
        names = [n for n in names if n not in self.projects]
        if not names:
            return
        def fetch(name):
            log.info("Fetch: %s", name)
            with urlopen("https://pypi.org/pypi/%s/json" % name) as f:
                return json.load(f)
        with ThreadPoolExecutor() as e:
            self.projects.update([name, self.PypiProject(data['releases'])]
                    for name, data in zip(names, invokeall([e.submit(fetch, name).result for name in names])))

    def writecudf(self, f):
        projects = list(self.projects.values())
        for p in projects:
            for cudfversion in p.cudfversions:
                f.write('package: %s\n' % p.info.config.name.replace(' ', ''))
                f.write('version: %s\n' % cudfversion)
                cudfdepends = p.cudfdepends(cudfversion)
                if cudfdepends:
                    f.write('depends: %s\n' % ', '.join(cudfdepends))
                f.write('\n')
        f.write('request: \n') # Space is needed apparently!
        f.write('install: %s\n' % ', '.join(p.info.config.name.replace(' ', '') for p in projects))
