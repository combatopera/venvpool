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
from .projectinfo import ProjectInfo
import os, subprocess, sys

setupformat = """import setuptools

def long_description():
    with open('README.md') as f:
        return f.read()

setuptools.setup(
        name = %r,
        version = %r,
        description = %r,
        long_description = %s,
        long_description_content_type = 'text/markdown',
        url = %r,
        author = %r,
        packages = setuptools.find_packages(),
        py_modules = %r,
        install_requires = %r,
        package_data = {'': ['*.pxd', '*.pyx', '*.pyxbld', '*.arid', '*.aridt']},
        scripts = %r,
        entry_points = {'console_scripts': %r})
"""
cfgformat = """[bdist_wheel]
universal=%s
"""

def pipify(info, release):
    description, url = info.descriptionandurl() if release else [None, None]
    version = info.nextversion() if release else workingversion
    with open(os.path.join(info.projectdir, 'setup.py'), 'w') as f:
        f.write(setupformat % (
                info['name'],
                version,
                description,
                'long_description()' if release else repr(None),
                url,
                info['author'] if release else None,
                info.py_modules(),
                info.allrequires() if release else info.remoterequires(),
                info.scripts(),
                info.console_scripts()))
    with open(os.path.join(info.projectdir, 'setup.cfg'), 'w') as f:
        f.write(cfgformat % int({2, 3} <= set(info['pyversions'])))
    return version

def main_pipify():
    info = ProjectInfo('.')
    pipify(info, False)
    subprocess.check_call([sys.executable, 'setup.py', 'egg_info'], cwd = info.projectdir)
