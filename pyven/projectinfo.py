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

from __future__ import with_statement
from .files import Files
from pkg_resources import parse_requirements
import aridity, logging, os, stat

log = logging.getLogger(__name__)

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
            parent = os.path.join(self.projectdir, '..')
            if os.path.abspath(parent) == os.path.abspath(self.projectdir):
                raise ProjectInfoNotFoundException(realdir)
            self.projectdir = parent
        self.info = aridity.Context()
        with aridity.Repl(self.info) as repl:
            repl.printf('requires := $list()')
            repl.printf('pyversions := $list()')
            repl.printf('proprietary = false')
            repl.printf('executable = false')
            repl.printf(". %s", os.path.abspath(infopath))

    def __getitem__(self, key):
        return self.info.resolved(key).unravel()

    def allrequires(self):
        return self['requires']

    def _parsedrequires(self):
        class Req:
            def __init__(self, reqstr, req):
                self.reqstr = reqstr
                self.namepart = req.unsafe_name # XXX: Is unsafe_name the correct attribute?
                self.specifier = req.specifier
            def isproject(this):
                return os.path.isdir(os.path.join(self.projectdir, '..', this.namepart))
        reqstrs = self.allrequires()
        return (Req(reqstr, req) for reqstr, req in zip(reqstrs, parse_requirements(reqstrs)))

    def localrequires(self):
        return [r.namepart for r in self._parsedrequires() if r.isproject()]

    def remoterequires(self):
        return [r.reqstr for r in self._parsedrequires() if not r.isproject()]

    def parsedremoterequires(self):
        return [r for r in self._parsedrequires() if not r.isproject()]

    def nextversion(self):
        import urllib.request, urllib.error, re, xml.dom.minidom as dom
        pattern = re.compile('-([0-9]+)[-.]')
        try:
            with urllib.request.urlopen("https://pypi.org/simple/%s/" % self['name']) as f:
                doc = dom.parseString(f.read())
            last = max(int(pattern.search(textcontent(a)).group(1)) for a in doc.getElementsByTagName('a'))
        except urllib.error.HTTPError as e:
            if 404 != e.code:
                raise
            last = 0
        return str(last + 1)

    def descriptionandurl(self):
        import urllib.request, json, re, subprocess
        originurl = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd = self.projectdir).decode()
        urlpath = re.search('^(?:git@github[.]com:|https://github[.]com/)(.+/.+)[.]git$', originurl).group(1)
        with urllib.request.urlopen("https://api.github.com/repos/%s" % urlpath) as f:
            return json.loads(f.read().decode())['description'], "https://github.com/%s" % urlpath

    def py_modules(self):
        suffix = '.py'
        return [name[:-len(suffix)] for name in os.listdir(self.projectdir) if name.endswith(suffix) and 'setup.py' != name and not name.startswith('test_')]

    def scripts(self):
        if not self['executable']:
            return []
        xmask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        def isscript(path):
            return os.stat(path).st_mode & xmask and not os.path.isdir(path)
        return [name for name in os.listdir(self.projectdir) if isscript(os.path.join(self.projectdir, name))]

    def console_scripts(self):
        import ast
        v = []
        prefix = 'main_'
        extension = '.py'
        for path in Files.relpaths(self.projectdir, [extension]):
            with open(os.path.join(self.projectdir, path)) as f:
                try:
                    m = ast.parse(f.read())
                except SyntaxError:
                    log.warning("Skip: %s" % path, exc_info = True)
                    continue
            for obj in m.body:
                if isinstance(obj, ast.FunctionDef) and obj.name.startswith(prefix):
                    v.append("%s=%s:%s" % (obj.name[len(prefix):], path[:-len(extension)].replace(os.sep, '.'), obj.name))
        return v
