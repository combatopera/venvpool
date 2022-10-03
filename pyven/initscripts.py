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

from .initopt import _hasname, _projectinfos
from diapyr.util import singleton
import logging, os, re, subprocess, venvpool

log = logging.getLogger(__name__)
scriptsparent = os.path.join(os.path.expanduser('~'), '.config', 'pyven')
dotpy = '.py'

@singleton
def scriptregex():
    main = '''(?:'__main__'|"__main__")'''
    return r"^if\s+(?:__name__\s*==\s*{main}|{main}\s*==\s*__name__)\s*:\s*$".format(**locals())

def _checkname(name):
    return not subprocess.call(['sh', '-c', "%s(){\n:;}" % name])

def main():
    venvpool.initlogging()
    if not os.path.exists(scriptsparent):
        os.makedirs(scriptsparent)
    with open(os.path.join(scriptsparent, 'scripts'), 'w') as f:
        for info in _projectinfos():
            if not _hasname(info):
                continue
            if not info.config.executable:
                log.debug("Not executable: %s", info.projectdir)
                continue
            log.info("Scan: %s", info.projectdir)
            ag = subprocess.Popen(['ag', '-l', '-G', re.escape(dotpy) + '$', scriptregex, info.projectdir], stdout = subprocess.PIPE, universal_newlines = True)
            for line in ag.stdout:
                path, = line.splitlines()
                name = os.path.basename(path)[:-len(dotpy)]
                if _checkname(name):
                    pyversion = max(info.config.pyversions)
                    f.write("""{name}() {{
    python{pyversion} '{venvpool.__file__}' '{path}' "$@"
}}
""".format(**dict(globals(), **locals())))
            assert ag.wait() in {0, 1}

if '__main__' == __name__:
    main()
