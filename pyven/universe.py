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

from diapyr.util import innerclass
from pkg_resources import parse_version
from urllib.parse import quote, unquote
from urllib.request import urlopen
import json, logging

log = logging.getLogger(__name__)

class Universe:

    @innerclass
    class Depend:

        def __init__(self, r):
            self.name = r.namepart
            s, = r.specifier
            self.exact = {'>=': False, '==': True}[s.operator]
            self.release = s.version

        def cudfstr(self):
            return "%s %s %s" % (self.name, '=' if self.exact else '>=', self._project(self.name).releasetocudfversion[self.release])

    class PypiProject:

        def __init__(self, name, releases):
            releases = [str(r) for r in sorted(map(parse_version, releases))]
            self.cudfversiontorelease = {1 + i: r for i, r in enumerate(releases)}
            self.releasetocudfversion = {r: 1 + i for i, r in enumerate(releases)}
            self.devcudfversion = len(releases) + 1
            self.name = name
            self.cudfversiontodepends = {v: [] for v in self.cudfversiontorelease}

        def toreq(self, cudfversion):
            return "%s==%s" % (self.name, self.cudfversiontorelease[cudfversion])

    @innerclass
    class EditableProject:

        cudfversiontorelease = 1,

        def __init__(self, info):
            self.name = info.config.name
            self.cudfversiontodepends = {1: [self.Depend(r) for r in info.parsedremoterequires()]}

        def toreq(self, cudfversion):
            assert 1 == cudfversion

    def __init__(self, editableinfos):
        self.projects = {i.config.name: self.EditableProject(i) for i in editableinfos}
        self.editables = list(self.projects.values())

    def _project(self, name):
        try:
            return self.projects[name]
        except KeyError:
            log.info("Fetch: %s", name)
            with urlopen("https://pypi.org/pypi/%s/json" % name) as f:
                self.projects[name] = p = self.PypiProject(name, json.load(f)['releases'])
            return p

    def writecudf(self, f):
        done = set()
        while done < self.projects.keys():
            projects = [p for name, p in self.projects.items() if name not in done]
            for p in projects:
                for cudfversion in p.cudfversiontorelease:
                    f.write('package: %s\n' % quote(p.name))
                    f.write('version: %s\n' % cudfversion)
                    depends = p.cudfversiontodepends[cudfversion]
                    if depends:
                        f.write('depends: %s\n' % ', '.join(d.cudfstr() for d in depends))
                    f.write('\n')
            done.update(p.name for p in projects)
        f.write('request: \n') # Space is needed apparently!
        f.write('install: %s\n' % ', '.join(quote(p.name) for p in self.editables))

    def toreq(self, cudfname, cudfversion):
        return self.projects[unquote(cudfname)].toreq(cudfversion)
