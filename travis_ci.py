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

import os, subprocess, itertools, pyven, tests, licheck

class MinicondaInfo:

    condaversion = '3.16.0'

    def __init__(self, title, dirname, envkey):
        self.title = title
        self.dirname = dirname
        self.envkey = envkey

pyversiontominicondainfo = {
    2: MinicondaInfo('Miniconda', 'miniconda', 'MINICONDA_HOME'),
    3: MinicondaInfo('Miniconda3', 'miniconda3', 'MINICONDA3_HOME'),
}

def installminicondas(infos, deps):
    for info in infos:
        if info.envkey in os.environ:
            continue
        scriptname = "%s-%s-Linux-x86_64.sh" % (info.title, info.condaversion)
        subprocess.check_call(['wget', '--no-verbose', "http://repo.continuum.io/miniconda/%s" % scriptname])
        command = ['bash', scriptname, '-b', '-p', info.dirname]
        subprocess.check_call(command)
        command = [os.path.join(info.dirname, 'bin', 'conda'), 'install', '-yq', 'pyflakes', 'nose']
        command.extend(deps)
        subprocess.check_call(command)
        os.environ[info.envkey] = os.path.join(os.getcwd(), info.dirname)

def main():
    conf = licheck.loadprojectinfo(licheck.infoname)
    projectdir = os.getcwd()
    os.chdir('..')
    for project in itertools.chain(['pyven'], conf['projects']):
        if not os.path.exists(project.replace('/', os.sep)): # Allow a project to depend on a subdirectory of itself.
            subprocess.check_call(['git', 'clone', "https://github.com/combatopera/%s.git" % project])
    os.environ['PATH'] = "%s%s%s" % (os.path.join(os.getcwd(), 'pyven'), os.pathsep, os.environ['PATH'])
    minicondainfos = [pyversiontominicondainfo[v] for v in conf['pyversions']]
    installminicondas(minicondainfos, conf['deps'])
    os.chdir(projectdir)
    for info in minicondainfos:
        # Equivalent to running tests.py directly but with one fewer process launch:
        pyven.mainimpl(projectdir, conf, [tests.__file__])

if '__main__' == __name__:
    main()
