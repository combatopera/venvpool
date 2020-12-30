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
from diapyr.util import innerclass
from packaging.utils import canonicalize_name
from pkg_resources import parse_version, safe_name
from pkg_resources.extern.packaging.requirements import InvalidRequirement
try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote
import logging

log = logging.getLogger(__name__)

class UnrenderableException(Exception): pass

class UnrenderableDepends:

    def __init__(self, cause):
        self.cause = cause

    def __iter__(self):
        raise UnrenderableException(self.cause)

class Names:

    def __init__(self, sname):
        self.cname = canonicalize_name(sname)
        self.qname = quote(self.cname)
        self.sname = sname

class Universe: # TODO: Less spammy logging.

    @innerclass
    class Depend:

        def __init__(self, req):
            self.names = Names(req.namepart)
            self.req = req

        def _cudfstrs(self):
            def ge():
                if release in lookup:
                    yield "%s >= %s" % (self.names.qname, lookup[release])
                else:
                    i = bisect(releases, release) - 1
                    if i >= 0:
                        yield "%s > %s" % (self.names.qname, lookup[releases[i]])
            def lt():
                if release in lookup:
                    yield "%s < %s" % (self.names.qname, lookup[release])
                else:
                    i = bisect(releases, release)
                    if i < len(releases):
                        yield "%s < %s" % (self.names.qname, lookup[releases[i]])
            lookup = self._project(self.names, self.req.specifierset.filter).releaseobjtocudfversion
            releases = list(lookup)
            for s in sorted(self.req.specifierset, key = str):
                release = parse_version(s.version)
                if '>=' == s.operator:
                    for x in ge(): yield x
                elif '<=' == s.operator:
                    if release in lookup:
                        yield "%s <= %s" % (self.names.qname, lookup[release])
                    else:
                        i = bisect(releases, release)
                        if i < len(releases):
                            yield "%s < %s" % (self.names.qname, lookup[releases[i]])
                elif '>' == s.operator:
                    if release in lookup:
                        yield "%s > %s" % (self.names.qname, lookup[release])
                    else:
                        i = bisect(releases, release) - 1
                        if i >= 0:
                            yield "%s > %s" % (self.names.qname, lookup[releases[i]])
                elif '<' == s.operator:
                    for x in lt(): yield x
                elif '!=' == s.operator:
                    if release in lookup:
                        yield "%s != %s" % (self.names.qname, lookup[release])
                elif '==' == s.operator:
                    if s.version.endswith('.*'):
                        release = parse_version(s.version[:-2])
                        for x in ge(): yield x
                        v = list(release._version.release)
                        v[-1] += 1
                        release = parse_version('.'.join(map(str, v)))
                        for x in lt(): yield x
                    else:
                        if release not in lookup:
                            raise UnrenderableException("No such %s release: %s" % (self.req.namepart, s.version))
                        yield "%s = %s" % (self.names.qname, lookup[release])
                elif '~=' == s.operator:
                    for x in ge(): yield x
                    v = list(release._version.release[:-1])
                    v[-1] += 1
                    release = parse_version('.'.join(map(str, v)))
                    for x in lt(): yield x
                else:
                    raise UnrenderableException("Unsupported requirement: %s" % self.req.reqstr)

        def cudfstr(self):
            s = ', '.join(self._cudfstrs())
            return s if s else self.names.qname

    @innerclass
    class PypiProject:

        editable = False

        def __init__(self, names, releases):
            releaseobjtostr = sorted((o, s) for o, s in zip(map(parse_version, releases), releases))
            self.cudfversiontoreleasestr = {1 + i: s for i, (_, s) in enumerate(releaseobjtostr)}
            self.releaseobjtocudfversion = {o: 1 + i for i, (o, _) in enumerate(releaseobjtostr)}
            self.cudfversiontodepends = {}
            self.names = names

        def fetch(self, filter):
            releaseobjs = [r for r in filter(self.releaseobjtocudfversion) if self.releaseobjtocudfversion[r] not in self.cudfversiontodepends]
            if releaseobjs:
                log.info("Fetch %s releases of: %s", len(releaseobjs), self.names.sname)
                for releaseobj in releaseobjs:
                    self.dependsof(self.releaseobjtocudfversion[releaseobj])

        def dependsof(self, cudfversion):
            try:
                return self.cudfversiontodepends[cudfversion]
            except KeyError:
                try:
                    reqs = self.pypicache.requires_dist(self.names.cname, self.cudfversiontoreleasestr[cudfversion])
                except Exception as e:
                    depends = UnrenderableDepends(e)
                else:
                    try:
                        depends = [self.Depend(r) for r in Req.parsemany(reqs) if r.accept()]
                    except InvalidRequirement as e:
                        depends = UnrenderableDepends(e)
                self.cudfversiontodepends[cudfversion] = depends
                return depends

        def reqornone(self, cudfversion):
            return "%s==%s" % (self.names.sname, self.cudfversiontoreleasestr[cudfversion])

    @innerclass
    class EditableProject:

        editable = True
        cudfversiontoreleasestr = {1: '-e'}

        def __init__(self, info):
            self.names = Names(safe_name(info.config.name))
            self.cudfversiontodepends = {1: [self.Depend(r) for r in info.parsedremoterequires() if r.accept()]}

        def dependsof(self, cudfversion):
            return self.cudfversiontodepends[cudfversion]

        def reqornone(self, cudfversion):
            assert 1 == cudfversion

    def __init__(self, pypicache, editableinfos):
        self.projects = {p.names.cname: p for p in map(self.EditableProject, editableinfos)}
        self.pypicache = pypicache

    def _project(self, names, fetchfilter):
        try:
            p = self.projects[names.cname]
        except KeyError:
            log.info("Fetch: %s", names.sname)
            self.projects[names.cname] = p = self.PypiProject(names, self.pypicache.releases(names.cname))
        p.fetch(fetchfilter)
        return p

    def writecudf(self, f): # FIXME: Uses far too much CPU.
        donereleases = set()
        while True:
            releasecount = sum(1 for cname in self.projects for cudfversion in self.projects[cname].cudfversiontodepends)
            if len(donereleases) == releasecount:
                break
            log.debug("Releases remaining: %s", releasecount - len(donereleases))
            for cname, p in list(self.projects.items()):
                for cudfversion in p.cudfversiontodepends:
                    if (cname, cudfversion) in donereleases:
                        continue
                    releasestr = p.cudfversiontoreleasestr[cudfversion]
                    try:
                        dependsstr = ', '.join(d.cudfstr() for d in p.dependsof(cudfversion))
                        f.write('# %s %s\n' % (p.names.sname, releasestr))
                        f.write('package: %s\n' % p.names.qname)
                        f.write('version: %s\n' % cudfversion)
                        if dependsstr:
                            f.write('depends: %s\n' % dependsstr)
                        f.write('conflicts: %s\n' % p.names.qname) # At most one version of package.
                        f.write('\n')
                    except UnrenderableException as e:
                        log.warning("Exclude %s==%s because: %s", p.names.sname, releasestr, e)
                    donereleases.add((cname, cudfversion))
        f.write('request: \n') # Space is needed apparently!
        f.write('install: %s\n' % ', '.join(quote(cname) for cname, p in self.projects.items() if p.editable))

    def reqornone(self, cudfname, cudfversion):
        return self.projects[unquote(cudfname)].reqornone(cudfversion)
