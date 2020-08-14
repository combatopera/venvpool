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

from . import checks
from .projectinfo import ProjectInfo
import os, requests, subprocess

class Workspace:

    bools = {str(b).lower(): b for b in [False, True]}
    user = 'combatopera'

    def __init__(self, workspace):
        self.projects = set(r['name'] for r in requests.get("https://api.github.com/users/%s/repos" % self.user).json()) if self.bools[os.environ['HEADS']] else []
        self.workspace = workspace

    def clonerequires(self, info):
        for req in info.allrequires():
            if req in self.projects:
                path = os.path.join(self.workspace, req)
                if not os.path.exists(path): # Allow for diamond dependencies.
                    subprocess.check_call(['git', 'clone', '-b', 'master', "https://github.com/%s/%s.git" % (self.user, req)], cwd = self.workspace)
                self.clonerequires(ProjectInfo.seek(path))

def main_travis_ci():
    info = ProjectInfo.seek('.')
    Workspace('..').clonerequires(info) # XXX: Use a subdirectory of here?
    with open('.gitignore', 'a') as f:
        f.write('/.pyven/\n')
    checks.everyversion(info, [])
