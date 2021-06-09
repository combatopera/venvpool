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

from .pypicache import PypiCache
from .universe import Universe
from .util import bgcontainer, cachedir
from datetime import datetime
from pkg_resources import resource_filename
import logging, os

log = logging.getLogger(__name__)

def legacy(args, infos):
    specifiers = {}
    for i in infos:
        for req in i.parsedremoterequires():
            s = specifiers.get(req.namepart)
            if s is None:
                s = req.specifierset
            else:
                log.debug("Intersect %s%s with: %s%s", req.namepart, s, req.namepart, req.specifierset)
                s &= req.specifierset
            specifiers[req.namepart] = s
    return ["%s%s" % entry for entry in specifiers.items()]

def mccs(args, infos):
    from lagoon import docker # FIXME: Port to subprocess for Python 2.
    from lagoon.program import NOEOL, partial
    solution = []
    with PypiCache(args, os.path.join(cachedir, 'pypi.shelf')) as pypicache:
        u = Universe(pypicache, infos)
        path = os.path.join(args.venvpath, "%s.cudf" % datetime.now().isoformat().replace(':', '-'))
        with open(path, 'w') as f:
            u.writecudf(f)
        build = docker.build[partial](resource_filename(__name__, 'mccs'))
        build._t.mccs(stdout = None)
        with bgcontainer('-v', "%s:/io/input.cudf" % path, build._q[NOEOL]()) as container:
            log.info("Run mccs solver, this can take a minute.")
            # TODO: Investigate why this may get stuck in an infinite loop.
            lines = [l for l in docker('exec', container, 'mccs', '-i', '/io/input.cudf', '-lexsemiagregate[-removed,-notuptodate,-new]').splitlines()
                    if l and not l.startswith(('#', 'depends:', 'conflicts:'))]
        while lines:
            k, package = lines.pop(0).split(' ') # TODO: Proper error on fail, and log on exit for timestamp.
            assert 'package:' == k
            k, versionstr = lines.pop(0).split(' ')
            assert 'version:' == k
            assert 'installed: true' == lines.pop(0)
            req = u.reqornone(package, int(versionstr))
            if req is not None:
                solution.append(req)
    return solution
