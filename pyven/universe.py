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

from .projectinfo import Req
from bisect import bisect
from concurrent.futures import ThreadPoolExecutor
from diapyr.util import innerclass
from hashlib import md5
from pkg_resources import parse_version
from pkg_resources.extern.packaging.requirements import InvalidRequirement
from splut import invokeall
from urllib.parse import quote, unquote
import gzip, json, logging, os, shutil, urllib.request

log = logging.getLogger(__name__)
mirrordir = os.path.join(os.path.expanduser('~'), '.pyven', 'mirror')

def urlopen(url):
    mirrorpath = os.path.join(mirrordir, md5(url.encode('ascii')).hexdigest())
    if not os.path.exists(mirrorpath):
        os.makedirs(os.path.dirname(mirrorpath), exist_ok = True)
        partialpath = "%s.part" % mirrorpath
        with urllib.request.urlopen(url) as f, gzip.open(partialpath, 'wb') as g:
            shutil.copyfileobj(f, g)
        os.rename(partialpath, mirrorpath)
    return gzip.open(mirrorpath, 'rb')

class UnrenderableException(Exception): pass

class UnrenderableDepends:

    def __init__(self, cause):
        self.cause = cause

    def __iter__(self):
        raise UnrenderableException(self.cause)

class Universe:

    @innerclass
    class Depend:

        def __init__(self, req):
            self.req = req

        def _cudfstrs(self):
            name = self.req.namepart
            lookup = self._project(name).releasetocudfversion # TODO: Fetch heuristic.
            releases = list(lookup)
            for s in self.req.specifier:
                release = parse_version(s.version)
                if '>=' == s.operator:
                    if release in lookup:
                        yield "%s >= %s" % (name, lookup[release])
                    else:
                        i = bisect(releases, release) - 1
                        if i >= 0:
                            yield "%s > %s" % (name, lookup[releases[i]])
                elif '<=' == s.operator:
                    if release in lookup:
                        yield "%s <= %s" % (name, lookup[release])
                    else:
                        i = bisect(releases, release)
                        if i < len(releases):
                            yield "%s < %s" % (name, lookup[releases[i]])
                elif '>' == s.operator:
                    if release in lookup:
                        yield "%s > %s" % (name, lookup[release])
                    else:
                        i = bisect(releases, release) - 1
                        if i >= 0:
                            yield "%s > %s" % (name, lookup[releases[i]])
                elif '<' == s.operator:
                    if release in lookup:
                        yield "%s < %s" % (name, lookup[release])
                    else:
                        i = bisect(releases, release)
                        if i < len(releases):
                            yield "%s < %s" % (name, lookup[releases[i]])
                elif '!=' == s.operator:
                    if release in lookup:
                        yield "%s != %s" % (name, lookup[release])
                elif '==' == s.operator:
                    if release not in lookup:
                        raise UnrenderableException("No such %s release: %s" % (name, release))
                    yield "%s = %s" % (name, lookup[release])
                else:
                    print(name, s)
                    gerger

        def cudfstr(self):
            return ', '.join(self._cudfstrs()) if self.req.specifier else self.req.namepart

    @innerclass
    class PypiProject:

        editable = False

        def __init__(self, name, releases):
            releases = sorted(map(parse_version, releases))
            self.cudfversiontorelease = {1 + i: r for i, r in enumerate(releases)}
            self.releasetocudfversion = {r: 1 + i for i, r in enumerate(releases)}
            with ThreadPoolExecutor() as e:
                def fetch(release):
                    with urlopen("https://pypi.org/pypi/%s/%s/json" % (name, release)) as f:
                        reqs = json.load(f)['info']['requires_dist']
                    try:
                        return [] if reqs is None else [self.Depend(r) for r in Req.parsemany(reqs)]
                    except InvalidRequirement as e:
                        return UnrenderableDepends(e)
                self.cudfversiontodepends = dict(zip(self.cudfversiontorelease, invokeall([e.submit(fetch, release).result for release in releases])))
            self.name = name

        def toreq(self, cudfversion):
            return "%s==%s" % (self.name, self.cudfversiontorelease[cudfversion])

    @innerclass
    class EditableProject:

        editable = True
        cudfversiontorelease = {1: '-e'}

        def __init__(self, info):
            self.name = info.config.name
            self.cudfversiontodepends = {1: [self.Depend(r) for r in info.parsedremoterequires()]}

        def toreq(self, cudfversion):
            assert 1 == cudfversion

    def __init__(self, editableinfos):
        self.projects = {p.name: p for p in map(self.EditableProject, editableinfos)}

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
                for cudfversion, release in p.cudfversiontorelease.items():
                    try:
                        dependsstr = ', '.join(d.cudfstr() for d in p.cudfversiontodepends[cudfversion])
                        f.write('# %s %s\n' % (p.name, release))
                        f.write('package: %s\n' % quote(p.name))
                        f.write('version: %s\n' % cudfversion)
                        if dependsstr:
                            f.write('depends: %s\n' % dependsstr)
                        f.write('\n')
                    except UnrenderableException as e:
                        log.warning("Exclude %s==%s because: %s", p.name, release, e)
            done.update(p.name for p in projects)
        f.write('request: \n') # Space is needed apparently!
        f.write('install: %s\n' % ', '.join(quote(name) for name, p in self.projects.items() if p.editable))

    def toreq(self, cudfname, cudfversion):
        return self.projects[unquote(cudfname)].toreq(cudfversion)
