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
import os, sys, subprocess, shutil, argparse, logging

log = logging.getLogger(__name__)
setupformat = """import setuptools

def long_description():
    with open('README.md') as f:
        return f.read()

setuptools.setup(
        name = %r,
        version = %r,
        description = %r,
        long_description = long_description(),
        long_description_content_type = 'text/markdown',
        url = %r,
        author = %r,
        packages = setuptools.find_packages(),
        py_modules = %r,
        install_requires = %r,
        package_data = {'': ['*.pxd', '*.pyx', '*.pyxbld', '*.arid', '*.aridt']},
        scripts = %r)
"""
cfgformat = """[bdist_wheel]
universal=%s
"""

def main():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('--upload', action = 'store_true')
    parser.add_argument('path', nargs = '?', type = os.path.abspath, default = os.getcwd())
    config = parser.parse_args()
    info = ProjectInfo(config.path)
    with open(os.path.join(info.projectdir, 'setup.py'), 'w') as f:
        f.write(setupformat % ((info['name'], info.nextversion()) + info.descriptionandurl() + (info['author'], info.py_modules(), info['deps'] + info['projects'], info.scripts())))
    with open(os.path.join(info.projectdir, 'setup.cfg'), 'w') as f:
        f.write(cfgformat % int({2, 3} <= set(info['pyversions'])))
    dist = os.path.join(info.projectdir, 'dist')
    if os.path.isdir(dist):
        shutil.rmtree(dist) # Remove any previous versions.
    subprocess.check_call([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd = info.projectdir)
    if config.upload:
        subprocess.check_call([sys.executable, '-m', 'twine', 'upload'] + [os.path.join(dist, name) for name in os.listdir(dist)])
    else:
        log.warning('Upload skipped, use --upload to upload.')

if '__main__' == __name__:
    main()
