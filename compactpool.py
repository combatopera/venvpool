# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022 Andrzej Cichocki

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

'Use jdupes to combine identical files in the venv pool.'
from venvpool import initlogging, listorempty, pooldir, Venv
import logging, os, shutil, subprocess

log = logging.getLogger(__name__)

def main(): # XXX: Combine venvs with orthogonal dependencies?
    initlogging()
    locked = []
    try:
        for versiondir in listorempty(pooldir):
            for venv in listorempty(versiondir, Venv):
                if venv.trywritelock():
                    locked.append(venv)
                else:
                    log.debug("Busy: %s", venv.venvpath)
        _compactvenvs([l.venvpath for l in locked])
    finally:
        for l in reversed(locked):
            if os.path.exists(l.venvpath):
                l.writeunlock()

def _compactvenvs(venvpaths):
    log.info("Compact %s venvs.", len(venvpaths))
    freezes = {}
    for venvpath in venvpaths:
        freezes[venvpath] = set(subprocess.check_output([os.path.join(venvpath, 'bin', 'pip'), 'freeze'], universal_newlines = True).splitlines())
    for venvpath, freeze in freezes.items():
        for otherpath, otherfreeze in freezes.items():
            if venvpath != otherpath and os.path.exists(otherpath) and os.path.dirname(venvpath) == os.path.dirname(otherpath) and freeze <= otherfreeze:
                log.info("Delete redundant venv: %s", venvpath)
                shutil.rmtree(venvpath)
                venvpaths.remove(venvpath)
                break
    if venvpaths:
        subprocess.check_call(['jdupes', '-Lrq'] + venvpaths)
    log.info('Compaction complete.')

if '__main__' == __name__:
    main()
