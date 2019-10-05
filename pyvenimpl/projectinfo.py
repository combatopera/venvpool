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

from __future__ import with_statement
import os, sys
d = os.path.dirname(os.path.realpath(__file__)) # pyvenimpl
d = os.path.dirname(d) # pyven
d = os.path.dirname(d) # workspace
sys.path.append(os.path.join(d, 'aridity'))
del d
import aridity

class ProjectInfoNotFoundException(Exception): pass

def textcontent(node):
    def iterparts(node):
        value = node.nodeValue
        if value is None:
            for child in node.childNodes:
                for text in iterparts(child):
                    yield text
        else:
            yield value
    return ''.join(iterparts(node))

class ProjectInfo:

    def __init__(self, realdir):
        self.projectdir = realdir
        while True:
            infopath = os.path.join(self.projectdir, 'project.arid')
            if os.path.exists(infopath):
                break
            parent = os.path.dirname(self.projectdir)
            if parent == self.projectdir:
                raise ProjectInfoNotFoundException(realdir)
            self.projectdir = parent
        self.info = aridity.Context()
        with aridity.Repl(self.info) as repl:
            repl.printf('projects := $list()')
            repl.printf('branch := $fork()')
            repl.printf('deps := $list()')
            repl.printf('pyversions := $list()')
            repl.printf('proprietary = false')
            repl.printf(". %s", infopath)

    def __getitem__(self, key):
        return self.info.resolved(key).unravel()

    def nextversion(self):
        import urllib.request, urllib.error, roman, re, xml.dom.minidom as dom
        pattern = re.compile('-([0-9]+|[IVXLCDM]+)[-.]')
        def toint(version):
            try:
                return int(version)
            except ValueError:
                return roman.fromRoman(version)
        try:
            with urllib.request.urlopen("https://pypi.org/simple/%s/" % self['name']) as f:
                doc = dom.parseString(f.read())
            last = max(toint(pattern.search(textcontent(a)).group(1)) for a in doc.getElementsByTagName('a'))
        except urllib.error.HTTPError as e:
            if 404 != e.code:
                raise
            last = 0
        return roman.toRoman(last + 1)
