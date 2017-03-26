#!/usr/bin/env python

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

import os, subprocess, pyven, tests, licheck

class MinicondaInfo:

    condaversion = '3.16.0'
    opt = os.path.join(os.path.expanduser('~'), 'opt')

    def __init__(self, title, dirname, envkey):
        self.scriptname = "%s-%s-Linux-x86_64.sh" % (title, self.condaversion)
        self.home = os.path.join(self.opt, dirname)
        self.envkey = envkey

    def installifnecessary(self, deps):
        if self.envkey in os.environ:
            return # Already installed.
        for path in self.scriptname, self.home:
            if os.path.exists(path):
                raise Exception(path) # Panic.
        subprocess.check_call(['wget', '--no-verbose', "http://repo.continuum.io/miniconda/%s" % self.scriptname])
        command = ['bash', self.scriptname, '-b', '-p', self.home]
        subprocess.check_call(command)
        os.remove(self.scriptname)
        command = [os.path.join(self.home, 'bin', 'conda'), 'install', '-yq', 'pyflakes', 'nose']
        command.extend(deps)
        subprocess.check_call(command)
        os.environ[self.envkey] = self.home

pyversiontominicondainfo = {
    2: MinicondaInfo('Miniconda', 'miniconda', 'MINICONDA_HOME'),
    3: MinicondaInfo('Miniconda3', 'miniconda3', 'MINICONDA3_HOME'),
}

def main():
    conf = licheck.loadprojectinfo(licheck.infoname)
    projectdir = os.getcwd()
    os.chdir('..')
    for project in conf['projects']:
        if not os.path.exists(project.replace('/', os.sep)): # Allow a project to depend on a subdirectory of itself.
            subprocess.check_call(['git', 'clone', "https://github.com/combatopera/%s.git" % project])
    os.chdir(projectdir)
    minicondainfos = [pyversiontominicondainfo[v] for v in conf['pyversions']]
    for info in minicondainfos:
        info.installifnecessary(conf['deps'])
    for info in minicondainfos:
        # Equivalent to running tests.py directly but with one fewer process launch:
        pyven.mainimpl(projectdir, conf, [tests.__file__])

if '__main__' == __name__:
    main()
