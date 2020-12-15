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
from datetime import datetime
import logging, os, subprocess

log = logging.getLogger(__name__)

def legacy(venvpath, infos):
    specifiers = {}
    for i in infos:
        for req in i.parsedremoterequires():
            s = specifiers.get(req.namepart)
            if s is None:
                s = req.specifier
            else:
                log.debug("Intersect %s%s with: %s%s", req.namepart, s, req.namepart, req.specifier)
                s &= req.specifier
            specifiers[req.namepart] = s
    return ["%s%s" % entry for entry in specifiers.items()]

def mccs(venvpath, infos):
    solution = []
    with PypiCache(os.path.join(os.path.expanduser('~'), '.pyven', 'pypi.shelf')) as pypicache:
        u = Universe(pypicache, infos)
        path = os.path.join(venvpath, "%s.cudf" % datetime.now().isoformat())
        with open(path, 'w') as f:
            u.writecudf(f)
        log.info("Run mccs solver, this can take a minute.")
        # TODO: Investigate why this may get stuck in an infinite loop.
        lines = [l for l in subprocess.check_output(['mccs', '-i', path, '-lexsemiagregate[-removed,-notuptodate,-new]'], universal_newlines = True).splitlines()
                if l and not l.startswith(('#', 'depends:', 'conflicts:'))]
        while lines:
            k, package = lines.pop(0).split(' ')
            assert 'package:' == k
            k, versionstr = lines.pop(0).split(' ')
            assert 'version:' == k
            assert 'installed: true' == lines.pop(0)
            req = u.reqornone(package, int(versionstr))
            if req is not None:
                solution.append(req)
    return solution
