# Copyright 2013, 2014, 2015, 2016 Andrzej Cichocki

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

class MinicondaInfo:

    condaversion = '3.16.0'
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
                raise Exception(path) # Panic.
        subprocess.check_call(['wget', '--no-verbose', "http://repo.continuum.io/miniconda/%s" % self.scriptname])
        command = ['bash', self.scriptname, '-b', '-p', self.target]
        subprocess.check_call(command)
        os.remove(self.scriptname)
        command = [os.path.join(self.target, 'bin', 'conda'), 'install', '-yq', 'pyflakes', 'nose']
        command.extend(deps)
        subprocess.check_call(command)
        os.environ[self.envkey] = self.target

    def path(self):
        return os.environ[self.envkey]

pyversiontominicondainfo = {info.pyversion: info for info in [
    MinicondaInfo(2, 'Miniconda', 'miniconda', 'MINICONDA_HOME'),
    MinicondaInfo(3, 'Miniconda3', 'miniconda3', 'MINICONDA3_HOME'),
]}
