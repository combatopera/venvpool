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
import logging, os, re, sys, venvpool

log = logging.getLogger(__name__)
executablebits = S_IXUSR | S_IXGRP | S_IXOTH
scriptpattern = re.compile(scriptregex, re.MULTILINE)
userbin = os.path.join(os.path.expanduser('~'), '.local', 'bin')

def _projectinfos():
    cc = ConfigCtrl()
    cc.loadsettings()
    projectsdir = cc.node.projectsdir
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

def _srcpaths(rootdir):
    for dirpath, dirnames, filenames in os.walk(rootdir):
        for name in filenames:
            if name.endswith(dotpy):
                path = os.path.join(dirpath, name)
                with open(path) as f:
                    if scriptpattern.search(f.read()) is not None:
                        yield path

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
        scan(info.projectdir, userbin, max(info.config.pyversions), venvpool.__file__)

def scan(projectdir, bindir, pyversion, venvpoolpath):
    for srcpath in _srcpaths(projectdir):
        if not checkpath(projectdir, srcpath):
            log.debug("Not a project source file: %s", srcpath)
            continue
        command = commandornone(srcpath)
        if command is None:
            log.debug("Bad source name: %s", srcpath)
            continue
        scriptpath = os.path.join(bindir, command)
        with open(scriptpath, 'w') as f:
            f.write("""#!/usr/bin/env python{pyversion}
import sys
sys.argv[1:1] = '--', {srcpath!r}
__file__ = {venvpoolpath!r}
with open(__file__) as f: text = f.read()
del sys, f
exec('del text\\n' + text)
""".format(**locals()))
        os.chmod(scriptpath, os.stat(scriptpath).st_mode | executablebits)

if ('__main__' == __name__):
    main()
