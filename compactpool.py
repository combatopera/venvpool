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
import logging, os, subprocess

log = logging.getLogger(__name__)

def main(): # XXX: Combine venvs with orthogonal dependencies?
    initlogging()
    venvtofreeze = {}
    try:
        for versiondir in listorempty(pooldir):
            for venv in listorempty(versiondir, Venv):
                if venv.trywritelock():
                    venvtofreeze[venv] = set(subprocess.check_output([venv.programpath('pip'), 'freeze'], universal_newlines = True).splitlines())
                else:
                    log.debug("Busy: %s", venv.venvpath)
        log.info('Find redundant venvs.')
        while True:
            venv = _redundantvenv(venvtofreeze)
            if venv is None:
                break
            venv.delete('redundant')
            venvtofreeze.pop(venv)
        _compactvenvs([l.venvpath for l in venvtofreeze])
    finally:
        for l in venvtofreeze:
            l.writeunlock()

def _redundantvenv(venvtofreeze):
    for venv, freeze in venvtofreeze.items():
        for othervenv, otherfreeze in venvtofreeze.items():
            if venv != othervenv and os.path.dirname(venv.venvpath) == os.path.dirname(othervenv.venvpath) and freeze <= otherfreeze:
                return venv

def _compactvenvs(venvpaths):
    log.info("Compact %s venvs.", len(venvpaths))
    if venvpaths:
        subprocess.check_call(['jdupes', '-Lrq'] + venvpaths)
    log.info('Compaction complete.')

if '__main__' == __name__:
    main()
