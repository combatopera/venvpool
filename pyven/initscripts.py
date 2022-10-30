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

from .mainmodules import checkpath, commandornone, scriptregex
from .projectinfo import ProjectInfo
from .setuproot import setuptoolsinfo
from aridity.config import ConfigCtrl
from aridity.util import dotpy
from stat import S_IXUSR, S_IXGRP, S_IXOTH
import logging, os, re, subprocess, sys, venvpool

log = logging.getLogger(__name__)
executablebits = S_IXUSR | S_IXGRP | S_IXOTH
userbin = os.path.join(os.path.expanduser('~'), '.local', 'bin')

def _projectinfos():
    config = ConfigCtrl()
    config.loadsettings()
    projectsdir = config.node.projectsdir
    for p in sorted(os.listdir(projectsdir)):
        projectdir = os.path.join(projectsdir, p)
        if os.path.exists(os.path.join(projectdir, ProjectInfo.projectaridname)):
            yield ProjectInfo.seek(projectdir)
        else:
            setuppath = os.path.join(projectdir, 'setup.py')
            if os.path.exists(setuppath):
                if sys.version_info.major < 3:
                    log.debug("Ignore: %s", projectdir)
                else:
                    yield setuptoolsinfo(setuppath)

def main():
    venvpool.initlogging()
    for info in _projectinfos():
        if not hasattr(info.config, 'name'):
            log.debug("Skip: %s", info.projectdir)
            continue
        if not info.config.executable:
            log.debug("Not executable: %s", info.projectdir)
            continue
        log.info("Scan: %s", info.projectdir)
        ag = subprocess.Popen(['ag', '-l', '-G', re.escape(dotpy) + '$', scriptregex, info.projectdir], stdout = subprocess.PIPE, universal_newlines = True)
        for line in ag.stdout:
            srcpath, = line.splitlines()
            if not checkpath(info.projectdir, srcpath):
                log.debug("Not a project source file: %s", srcpath)
                continue
            command = commandornone(srcpath)
            if command is None:
                log.debug("Bad source name: %s", srcpath)
                continue
            binpath = os.path.join(userbin, command)
            pyversion = max(info.config.pyversions)
            with open(binpath, 'w') as f:
                f.write("""#!/usr/bin/env python{pyversion}
import sys
sys.argv[1:1] = {srcpath!r}, '--'
__file__ = {venvpool.__file__!r}
with open(__file__) as f: text = f.read()
del sys, f
exec('del text\\n' + text)
""".format(**dict(globals(), **locals())))
            os.chmod(binpath, os.stat(binpath).st_mode | executablebits)
        assert ag.wait() in {0, 1}

if ('__main__' == __name__):
    main()
