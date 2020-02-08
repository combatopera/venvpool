# Copyright 2013, 2014, 2015, 2016, 2017 Andrzej Cichocki

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

from .pipify import pipify
from .projectinfo import ProjectInfo
import os, subprocess

def executable(info, pyversion):
    venvpath = os.path.join(info.projectdir, '.pyven', str(pyversion))
    if not os.path.exists(venvpath):
        subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, venvpath])
        workspace = os.path.dirname(info.projectdir)
        # FIXME LATER: Add nested editables (recursively).
        editables = [ProjectInfo(os.path.join(workspace, name)) for name in info['projects']]
        for i in editables:
            pipify(i, False)
        subprocess.check_call([os.path.join(venvpath, 'bin', 'pip'), 'install', 'pyparsing', 'pyflakes', 'nose'] + info['deps'] + sum((['-e', i.projectdir] for i in editables), []))
    return os.path.join(venvpath, 'bin', 'python')
