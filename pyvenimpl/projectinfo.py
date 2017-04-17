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

import os, sys
d = os.path.dirname(os.path.realpath(__file__)) # pyvenimpl
d = os.path.dirname(d) # pyven
d = os.path.dirname(d) # workspace
sys.path.append(os.path.join(d, 'aridity'))
del d
import aridity

class ProjectInfoNotFoundException(Exception): pass

class ProjectInfo:

    def __init__(self, realdir):
        self.projectdir = realdir
        while True:
            infopath = os.path.join(self.projectdir, 'project.info')
            if os.path.exists(infopath):
                break
            parent = os.path.dirname(self.projectdir)
            if parent == self.projectdir:
                raise ProjectInfoNotFoundException(realdir)
            self.projectdir = parent
        self.info = aridity.Context()
        with aridity.Repl(self.info) as repl:
            repl.printf("source %s", infopath)

    def __getitem__(self, key):
        return self.info.resolved(key).unravel()