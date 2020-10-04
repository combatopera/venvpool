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
from . import targetremote
from .files import Files
from .util import initlogging
from aridity.config import Config
from pkg_resources import parse_requirements, resource_filename
from tempfile import mkdtemp
import logging, os, re, shutil, stat, subprocess

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

    def __init__(self, reqstr, req):
        self.reqstr = reqstr
        self.namepart = req.unsafe_name # XXX: Is unsafe_name the correct attribute?
        self.specifier = req.specifier

    def siblingpath(self, workspace):
        return os.path.join(workspace, self.namepart)

    def isproject(self, info):
        return os.path.exists(self.siblingpath(info.contextworkspace()))

    @classmethod
    def published(cls, venv, reqstrs):
        if reqstrs:
            reqs = cls.parsemany(reqstrs)
            names = {cls.namematch(line).group() for line in subprocess.check_output([venv.programpath('pip'), 'search'] + [r.namepart for r in reqs]).decode().splitlines()}
            for r in reqs:
                if r.namepart in names:
                    yield r.reqstr
                else:
                    log.warning("Never published: %s", r.namepart)

    def minstr(self):
        version, = (s.version for s in self.specifier if s.operator in {'>=', '=='})
        return "%s==%s" % (self.namepart, version)

def main_minreqs():
    initlogging()
    print("requires = $list(%s)" % ' '.join(r.minstr() for r in ProjectInfo.seek('.').parsedrequires()))

class ProjectInfo:

    @classmethod
    def seek(cls, realdir):
        projectdir = realdir
        while True:
            infopath = os.path.join(projectdir, 'project.arid')
            if os.path.exists(infopath):
                return cls(projectdir, infopath)
            parent = os.path.join(projectdir, '..')
            if os.path.abspath(parent) == os.path.abspath(projectdir):
                raise ProjectInfoNotFoundException(realdir)
            projectdir = parent

    def __init__(self, projectdir, infopath):
        self.config = Config.blank()
        for path in resource_filename(__name__, 'projectinfo.arid'), os.path.abspath(infopath):
            self.config.load(path)
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
                doc = dom.parseString(f.read())
            last = max(int(pattern.search(textcontent(a)).group(1)) for a in doc.getElementsByTagName('a'))
        except urllib.error.HTTPError as e:
            if 404 != e.code:
                raise
            last = 0
        return str(last + 1)

    def descriptionandurl(self):
        import urllib.request, json, re, subprocess
        def originurls():
            for line in subprocess.check_output(['git', 'remote', '-v'], cwd = self.projectdir).decode().splitlines():
                fields = re.findall(r'\S+', line)
                if targetremote == fields[0]:
                    yield fields[1]
        originurl, = set(originurls())
        urlpath = re.search('^(?:git@github[.]com:|https://github[.]com/)(.+/.+)[.]git$', originurl).group(1)
        with urllib.request.urlopen("https://api.github.com/repos/%s" % urlpath) as f:
            return json.loads(f.read().decode())['description'], "https://github.com/%s" % urlpath

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

    def console_scripts(self):
        import ast
        v = []
        prefix = 'main_'
        extension = '.py'
        for path in Files.relpaths(self.projectdir, [extension], []):
            with open(os.path.join(self.projectdir, path)) as f:
                try:
                    m = ast.parse(f.read())
                except SyntaxError:
                    log.warning("Skip: %s" % path, exc_info = True)
                    continue
            for obj in m.body:
                if isinstance(obj, ast.FunctionDef) and obj.name.startswith(prefix):
                    v.append("%s=%s:%s" % (obj.name[len(prefix):].replace('_', '-'), path[:-len(extension)].replace(os.sep, '.'), obj.name))
        return v

    def installdeps(self, venv, siblings, localrepo):
        from .pipify import pipify
        workspace = mkdtemp()
        try:
            editableprojects = {}
            volatileprojects = {}
            pypireqs = []
            def adddeps(i, root):
                for r in i.parsedrequires():
                    name = r.namepart
                    if name in editableprojects or name in volatileprojects:
                        continue
                    if siblings:
                        siblingpath = r.siblingpath(i.contextworkspace())
                        if os.path.exists(siblingpath):
                            editableprojects[name] = j = self.seek(siblingpath)
                            yield j
                            continue
                    if localrepo is not None:
                        repopath = os.path.join(localrepo, "%s.git" % name)
                        if os.path.exists(repopath):
                            if siblings:
                                log.warning("Not a sibling, install from repo: %s", name)
                            clonepath = os.path.join(workspace, name)
                            subprocess.check_call(['git', 'clone', '--depth', '1', "file://%s" % repopath, clonepath])
                            volatileprojects[name] = j = self.seek(clonepath)
                            yield j
                            continue
                    if root: # Otherwise pip will handle it.
                        pypireqs.append(r.reqstr)
            infos = [self]
            isroot = True
            while infos:
                log.debug("Examine deps of: %s", ', '.join(i.config.name for i in infos))
                nextinfos = []
                for i in infos:
                    nextinfos.extend(adddeps(i, isroot))
                infos = nextinfos
                isroot = False
            for i in volatileprojects.values(): # Assume editables already pipified.
                pipify(i)
            pypireqs = list(Req.published(venv, pypireqs))
            venv.install(sum((['-e', i.projectdir] for i in editableprojects.values()), []) + [i.projectdir for i in volatileprojects.values()] + pypireqs)
        finally:
            shutil.rmtree(workspace)
