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

from .files import Files
from .setuproot import setuptoolsinfo
from .util import initlogging, Path
from aridity.config import ConfigCtrl
from aridity.util import openresource
from pkg_resources import parse_requirements
from pkg_resources.extern.packaging.markers import UndefinedEnvironmentName
import logging, os, re, stat, subprocess

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

class Req:

    namematch = re.compile(r'\S+').search

    @classmethod
    def parsemany(cls, reqstrs):
        return [cls(reqstr, req) for reqstr, req in zip(reqstrs, parse_requirements(reqstrs))]

    @property
    def namepart(self):
        return self.parsed.name

    @property
    def specifierset(self):
        return self.parsed.specifier

    def __init__(self, reqstr, req):
        self.reqstr = reqstr
        self.parsed = req

    def siblingpath(self, workspace):
        return os.path.join(workspace, self.namepart)

    def isproject(self, info):
        return os.path.exists(self.siblingpath(info.contextworkspace()))

    @classmethod
    def published(cls, reqstrs):
        from http import HTTPStatus
        from urllib.error import HTTPError
        from urllib.parse import quote
        from urllib.request import Request, urlopen
        for r in cls.parsemany(reqstrs):
            try:
                with urlopen(Request("https://pypi.org/simple/%s/" % quote(r.namepart, safe = ''), method = 'HEAD')):
                    pass
                yield r
            except HTTPError as e:
                if e.code != HTTPStatus.NOT_FOUND:
                    raise
                log.warning("Never published: %s", r.namepart)

    def minstr(self):
        version, = (s.version for s in self.specifierset if s.operator in {'>=', '=='})
        return "%s==%s" % (self.namepart, version)

    def accept(self):
        marker = self.parsed.marker
        try:
            if marker is None or marker.evaluate():
                assert not self.parsed.extras # Not supported.
                return True
        except UndefinedEnvironmentName:
            pass

    def keyversion(self):
        s, = self.specifierset
        return self.parsed.key, s.version

def main_minreqs():
    'Print project.arid snippet pinning requires to their minimum allowed versions.'
    initlogging()
    print("requires = $list(%s)" % ' '.join(r.minstr() for r in ProjectInfo.seek('.').parsedrequires()))

class ProjectInfo:

    projectaridname = 'project.arid'

    @classmethod
    def seek(cls, realdir):
        path = Path.seek(realdir, cls.projectaridname)
        if path is None:
            raise ProjectInfoNotFoundException(realdir)
        return cls(path.parent, path)

    @classmethod
    def seekany(cls, realdir):
        try:
            return cls.seek(realdir)
        except ProjectInfoNotFoundException:
            pass
        setuppath = Path.seek(realdir, 'setup.py')
        if setuppath is not None:
            log.info('Use setuptools mode.')
            return setuptoolsinfo(setuppath)
        log.info('Use uninstallable mode.')
        projectdir = os.path.dirname(Path.seek(realdir, '.git'))
        with openresource(__name__, 'setuproot/setuptools.arid') as f:
            info = cls(projectdir, f)
        info.config.name = os.path.basename(os.path.abspath(projectdir))
        return info

    def __init__(self, projectdir, infopathorstream):
        config = ConfigCtrl()
        with openresource(__name__, 'projectinfo.arid', 'utf-8') as f:
            config.load(f)
        config.load(infopathorstream)
        self.config = config.node
        self.projectdir = projectdir

    def mitpath(self):
        return os.path.join(self.projectdir, self.config.MIT.path)

    def contextworkspace(self):
        return os.path.join(self.projectdir, '..')

    def allrequires(self):
        return list(self.config.requires)

    def parsedrequires(self):
        return Req.parsemany(self.allrequires())

    def localrequires(self):
        return [r.namepart for r in self.parsedrequires() if r.isproject(self)]

    def remoterequires(self):
        return [r.reqstr for r in self.parsedrequires() if not r.isproject(self)]

    def parsedremoterequires(self):
        return [r for r in self.parsedrequires() if not r.isproject(self)]

    def nextversion(self): # XXX: Deduce from tags instead?
        import urllib.request, urllib.error, re, xml.dom.minidom as dom
        pattern = re.compile('-([0-9]+)[-.]')
        try:
            with urllib.request.urlopen("https://pypi.org/simple/%s/" % self.config.name) as f:
                doc = dom.parseString(subprocess.check_output(['tidy', '-asxml'], input = f.read()))
            last = max(int(pattern.search(textcontent(a)).group(1)) for a in doc.getElementsByTagName('a'))
        except urllib.error.HTTPError as e:
            if 404 != e.code:
                raise
            last = 0
        return str(last + 1)

    def descriptionandurl(self):
        import urllib.error, urllib.request, json, time
        urlpath = "combatopera/%s" % self.config.name # TODO: Make configurable.
        while True:
            try:
                with urllib.request.urlopen("https://api.github.com/repos/%s" % urlpath) as f:
                    return json.loads(f.read().decode())['description'], "https://github.com/%s" % urlpath
            except urllib.error.HTTPError as e:
                if 403 != e.code:
                    raise
                log.info("Sleep 1 minute due to: %s", e)
                time.sleep(60)

    def py_modules(self):
        suffix = '.py'
        return [name[:-len(suffix)] for name in os.listdir(self.projectdir) if name.endswith(suffix) and 'setup.py' != name and not name.startswith('test_')]

    def scripts(self):
        if not self.config.executable:
            return []
        xmask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        def isscript(path):
            return os.stat(path).st_mode & xmask and not os.path.isdir(path)
        return [name for name in os.listdir(self.projectdir) if isscript(os.path.join(self.projectdir, name))]

    def mainfunctions(self):
        import ast
        for path in Files.relpaths(self.projectdir, [MainFunction.extension], []):
            with open(os.path.join(self.projectdir, path)) as f:
                try:
                    m = ast.parse(f.read())
                except SyntaxError:
                    log.warning("Skip: %s" % path, exc_info = True)
                    continue
            for obj in m.body:
                if isinstance(obj, ast.FunctionDef) and obj.name.startswith(MainFunction.prefix):
                    yield MainFunction(path, obj)

    def console_scripts(self):
        return [mf.console_script for mf in self.mainfunctions()]

    def devversion(self):
        releases = [int(t[1:]) for t in subprocess.check_output(['git', 'tag'], cwd = self.projectdir, universal_newlines = True).splitlines() if 'v' == t[0]]
        return "%s.dev0" % ((max(releases) if releases else 0) + 1)

class MainFunction:

    prefix = 'main_'
    extension = '.py'

    def __init__(self, path, obj):
        import ast
        self.name = obj.name[len(self.prefix):].replace('_', '-')
        self.console_script = "%s=%s:%s" % (self.name, path[:-len(self.extension)].replace(os.sep, '.'), obj.name)
        self.doc = ast.get_docstring(obj)
