#!/usr/bin/env python3

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

from pyvenimpl.projectinfo import ProjectInfo
import os, sys, subprocess, stat, shutil

setupformat = """import setuptools

setuptools.setup(
        name = %r,
        version = %r,
        install_requires = %r,
        packages = setuptools.find_packages(),
        py_modules = %r,
        scripts = %r)
"""
cfgformat = """[bdist_wheel]
universal=%s
"""
xmask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

def isscript(path):
    return os.stat(path).st_mode & xmask and not os.path.isdir(path)

def getinfo():
    args = sys.argv[1:]
    if args:
        path, = args
        path = os.path.abspath(path)
    else:
        path = os.getcwd()
    return ProjectInfo(path)

def main():
    info = getinfo()
    py_modules = [name[:-len('.py')] for name in os.listdir(info.projectdir) if name.endswith('.py') and 'setup.py' != name]
    scripts = [name for name in os.listdir(info.projectdir) if isscript(os.path.join(info.projectdir, name))]
    with open(os.path.join(info.projectdir, 'setup.py'), 'w') as f:
        f.write(setupformat % (info['name'], info.nextversion(), info['deps'] + info['projects'], py_modules, scripts))
    with open(os.path.join(info.projectdir, 'setup.cfg'), 'w') as f:
        f.write(cfgformat % int({2, 3} <= set(info['pyversions'])))
    dist = os.path.join(info.projectdir, 'dist')
    if os.path.isdir(dist):
        shutil.rmtree(dist)
    subprocess.check_call([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd = info.projectdir)
    command = [sys.executable, '-m', 'twine', 'upload'] + [os.path.join(dist, name) for name in os.listdir(dist)]
    print(command)
    return
    subprocess.check_call(command)

if '__main__' == __name__:
    main()
