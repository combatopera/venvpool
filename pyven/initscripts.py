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

from .projectinfo import ProjectInfo
from .setuproot import setuptoolsinfo
from aridity.config import ConfigCtrl
from aridity.util import dotpy
from diapyr.util import singleton
from stat import S_IXUSR, S_IXGRP, S_IXOTH
import logging, os, re, subprocess, sys, venvpool

log = logging.getLogger(__name__)
executablebits = S_IXUSR | S_IXGRP | S_IXOTH
userbin = os.path.join(os.path.expanduser('~'), '.local', 'bin')

def _ispyvenproject(projectdir):
    return os.path.exists(os.path.join(projectdir, ProjectInfo.projectaridname))

def _hasname(info):
    try:
        info.config.name
        return True
    except AttributeError:
        log.debug("Skip: %s", info.projectdir)

def _projectinfos():
    config = ConfigCtrl()
    config.loadsettings()
    projectsdir = config.node.projectsdir
    for p in sorted(os.listdir(projectsdir)):
        projectdir = os.path.join(projectsdir, p)
        if _ispyvenproject(projectdir):
            yield ProjectInfo.seek(projectdir)
        else:
            setuppath = os.path.join(projectdir, 'setup.py')
            if os.path.exists(setuppath):
                if sys.version_info.major < 3:
                    log.debug("Ignore: %s", projectdir)
                else:
                    yield setuptoolsinfo(setuppath)

@singleton
def scriptregex():
    main = '''(?:'__main__'|"__main__")'''
    return r"^if\s+(?:__name__\s*==\s*{main}|{main}\s*==\s*__name__)\s*:\s*$".format(**locals())

def _checkpath(projectdir, path):
    while True:
        path = os.path.dirname(path)
        if path == projectdir:
            return True
        if not os.path.exists(os.path.join(path, '__init__.py')):
            break

def _binpathornone(srcpath):
    name = os.path.basename(srcpath)
    name = os.path.basename(os.path.dirname(srcpath)) if '__init__.py' == name else name[:-len(dotpy)]
    if '-' not in name:
        return os.path.join(userbin, name.replace('_', '-'))

def main():
    venvpool.initlogging()
    for info in _projectinfos():
        if not _hasname(info):
            continue
        if not info.config.executable:
            log.debug("Not executable: %s", info.projectdir)
            continue
        log.info("Scan: %s", info.projectdir)
        ag = subprocess.Popen(['ag', '-l', '-G', re.escape(dotpy) + '$', scriptregex, info.projectdir], stdout = subprocess.PIPE, universal_newlines = True)
        for line in ag.stdout:
            srcpath, = line.splitlines()
            if not _checkpath(info.projectdir, srcpath):
                log.debug("Not a project source file: %s", srcpath)
                continue
            binpath = _binpathornone(srcpath)
            if binpath is None:
                log.debug("Bad source file name: %s", srcpath)
                continue
            pyversion = max(info.config.pyversions)
            with open(binpath, 'w') as f:
                f.write("""#!/usr/bin/env python{pyversion}
import sys
sys.argv[1:1] = {srcpath!r}, '--'
with open({venvpool.__file__!r}) as f: text = f.read()
del sys, f
exec('''del text
''' + text)
""".format(**dict(globals(), **locals())))
            os.chmod(binpath, os.stat(binpath).st_mode | executablebits)
        assert ag.wait() in {0, 1}

if ('__main__' == __name__):
    main()
