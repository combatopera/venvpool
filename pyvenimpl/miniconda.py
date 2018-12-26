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

import os, subprocess

class PathExistsException(Exception): pass

class Miniconda:

    condaversion = '4.3.21'
    opt = os.path.join(os.path.expanduser('~'), 'opt')

    def __init__(self, pyversion, title, dirname, envkey):
        self.pyversion = pyversion
        self.scriptname = "%s-%s-Linux-x86_64.sh" % (title, self.condaversion)
        self.target = os.path.join(self.opt, dirname)
        self.envkey = envkey

    def installifnecessary(self, deps):
        if self.envkey in os.environ:
            return # Already installed.
        for path in self.scriptname, self.target:
            if os.path.exists(path):
                raise PathExistsException(path) # Panic.
        subprocess.check_call(['wget', '--no-verbose', "http://repo.continuum.io/miniconda/%s" % self.scriptname])
        command = ['bash', self.scriptname, '-b', '-p', self.target]
        subprocess.check_call(command)
        os.remove(self.scriptname)
        command = [os.path.join(self.target, 'bin', 'pip'), 'install', 'pyflakes', 'nose'] # XXX: Why not pyparsing?
        command.extend(deps)
        subprocess.check_call(command)
        os.environ[self.envkey] = self.target

    def executable(self):
        return os.path.join(os.environ[self.envkey], 'bin', 'python')

class Jython:

    pyversion = 'jython'

    def executable(self):
        return 'jython'

pyversiontominiconda = {info.pyversion: info for info in [
    Miniconda(2, 'Miniconda2', 'miniconda', 'MINICONDA_HOME'),
    Miniconda(3, 'Miniconda3', 'miniconda3', 'MINICONDA3_HOME'),
    Jython(),
]}
