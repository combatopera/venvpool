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
from pkg_resources import parse_version
from splut import invokeall
from urllib.request import urlopen
import json, logging

log = logging.getLogger(__name__)

class Universe:

    class Project:

        def __init__(self, releases):
            releases = [str(r) for r in sorted(map(parse_version, releases))]
            self.releases = {1 + i: r for i, r in enumerate(releases)}
            self.cudfversions = {r: v for v, r in self.releases.items()}
            self.devcudfversion = len(self.releases) + 1

    def __init__(self, infos):
        self.projects = {}
        for i in infos:
            if not i.config.pypi.participant:
                self.projects[i.config.name] = self.Project([])
        self._update(i.config.name for i in infos if i.config.pypi.participant)

    def _update(self, names):
        names = [n for n in names if n not in self.projects]
        if not names:
            return
        def fetch(name):
            log.info("Fetch: %s", name)
            with urlopen("https://pypi.org/pypi/%s/json" % name) as f:
                return json.load(f)
        with ThreadPoolExecutor() as e:
            self.projects.update([n, self.Project(j['releases'])] for n, j in zip(names, invokeall([e.submit(fetch, n).result for n in names])))

    def devcudfversion(self, info):
        return self.projects[info.config.name].devcudfversion

    def cudfdepends(self, info):
        reqs = info.parsedremoterequires()
        self._update(r.namepart for r in reqs)
        def hmm(r):
            p = self.projects[r.namepart]
            bounds = ["%s %s %s" % (r.namepart, '=' if '==' == s.operator else s.operator, p.cudfversions[s.version]) for s in r.specifier]
            return ', '.join(bounds) if bounds else r.namepart
        return [hmm(r) for r in reqs]
