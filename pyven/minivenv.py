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

from . import workingversion
from .pipify import pipify
from .projectinfo import ProjectInfo
from pkg_resources import get_distribution
import os, subprocess

class Namespace:

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

def bindir(info, pyversion):
    venvpath = os.path.join(info.projectdir, '.pyven', str(pyversion))
    if not os.path.exists(venvpath):
        subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, venvpath])
        workspace = os.path.join(info.projectdir, '..')
        editables = {}
        def addprojects(i):
            for name in i.localrequires():
                if name not in editables:
                    editables[name] = j = ProjectInfo(os.path.join(workspace, name))
                    addprojects(j)
        addprojects(info)
        reqs = info.remoterequires() # A new list.
        pyvenname = 'pyven'
        pyvendist = get_distribution(pyvenname)
        if workingversion == pyvendist.version:
            addprojects(Namespace(localrequires = lambda: [pyvenname]))
        else:
            reqs = [r for r in reqs if r != pyvenname]
            reqs.append(str(pyvendist.as_requirement()))
        for i in editables.values():
            pipify(i, False)
        subprocess.check_call([os.path.join(venvpath, 'bin', 'pip'), 'install'] + reqs + sum((['-e', i.projectdir] for i in editables.values()), []))
    return os.path.join(venvpath, 'bin')
