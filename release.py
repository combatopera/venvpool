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
from urllib.error import HTTPError
import urllib.request, xml.dom.minidom as dom, re, os, sys, subprocess

def textcontent(node):
    def iterparts(node):
        value = node.nodeValue
        if value is None:
            for child in node.childNodes:
                for part in iterparts(child):
                    yield part
        else:
            yield value
    return ''.join(iterparts(node))

setupformat = """import setuptools

setuptools.setup(
        name = %r,
        version = %r,
        install_requires = %r,
        packages = setuptools.find_packages())
"""
cfgformat = """[bdist_wheel]
universal=%s
"""

def main():
    args = sys.argv[1:]
    if args:
        path, = args
        path = os.path.abspath(path)
    else:
        path = os.getcwd()
    info = ProjectInfo(path)
    try:
        with urllib.request.urlopen("https://pypi.org/simple/%s/" % info['name']) as f:
            doc = dom.parseString(f.read())
        last = max(int(re.search('[0-9]+', textcontent(a)).group()) for a in doc.getElementsByTagName('a'))
    except HTTPError as e:
        if 404 != e.code:
            raise
        last = 0
    with open(os.path.join(info.projectdir, 'setup.py'), 'w') as f:
        f.write(setupformat % (info['name'], str(last + 1), info['deps'] + info['projects']))
    with open(os.path.join(info.projectdir, 'setup.cfg'), 'w') as f:
        f.write(cfgformat % ({2, 3} <= set(info['pyversions'])))
    subprocess.check_call([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd = info.projectdir)
    dist = os.path.join(info.projectdir, 'dist')
    command = [sys.executable, '-m', 'twine', 'upload'] + [os.path.join(dist, name) for name in os.listdir(dist)]
    print(command)
    return
    subprocess.check_call(command)

if '__main__' == __name__:
    main()
