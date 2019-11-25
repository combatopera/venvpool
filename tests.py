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
from pyvenimpl import licheck as licheckimpl, nlcheck as nlcheckimpl, divcheck as divcheckimpl, execcheck as execcheckimpl, projectinfo
from pyvenimpl.util import stderr
import subprocess, sys, os, re, xml.dom.minidom as dom, collections

def stripeol(line):
    line, = line.splitlines()
    return line

class Files:

    reportpath = 'nosetests.xml'

    @staticmethod
    def findfiles(*suffixes):
        walkpath = '.'
        prefixlen = len(walkpath + os.sep)
        for dirpath, dirnames, filenames in os.walk(walkpath):
            for name in sorted(filenames):
                for suffix in suffixes:
                    if name.endswith(suffix):
                        yield os.path.join(dirpath, name)[prefixlen:]
                        break # Next name.
            dirnames.sort()

    @classmethod
    def filterfiles(cls, *suffixes):
        paths = list(cls.findfiles(*suffixes))
        if os.path.exists('.hg'):
            badstatuses = set('IR ')
            for line in subprocess.Popen(['hg', 'st', '-A'] + paths, stdout = subprocess.PIPE).stdout:
                line = stripeol(line).decode()
                if line[0] not in badstatuses:
                    yield line[2:]
        else:
            ignored = set(subprocess.Popen(['git', 'check-ignore'] + paths, stdout = subprocess.PIPE).communicate()[0].decode().splitlines())
            for path in paths:
                if path not in ignored:
                    yield path

    def __init__(self):
        self.allsrcpaths = list(p for p in self.filterfiles('.py', '.py3', '.pyx', '.s', '.sh', '.h', '.cpp', '.cxx', '.arid'))
        self.pypaths = [p for p in self.allsrcpaths if p.endswith('.py')]

    def testpaths(self):
        paths = [p for p in self.pypaths if os.path.basename(p).startswith('test_')]
        if os.path.exists(self.reportpath):
            with open(self.reportpath) as f:
                doc = dom.parse(f)
            nametopath = dict([p[:-len('.py')].replace(os.sep, '.'), p] for p in paths)
            pathtotime = collections.defaultdict(lambda: 0)
            for e in doc.getElementsByTagName('testcase'):
                name = e.getAttribute('classname')
                while True:
                    i = name.rfind('.')
                    if -1 == i:
                        break
                    name = name[:i]
                    if name in nametopath:
                        pathtotime[nametopath[name]] += float(e.getAttribute('time'))
                        break
            paths.sort(key = lambda p: pathtotime.get(p, float('inf')))
        return paths

def licheck(info, files):
    def g():
        for path in files.allsrcpaths:
            parentname = os.path.basename(os.path.dirname(path))
            if parentname != 'contrib' and not parentname.endswith('_turbo'):
                yield path
    licheckimpl.mainimpl(info, list(g()))

def nlcheck(info, files):
    nlcheckimpl.mainimpl(files.allsrcpaths)

def divcheck(info, files):
    divcheckimpl.mainimpl(files.pypaths)

def execcheck(info, files):
    execcheckimpl.mainimpl(files.pypaths)

def pyflakes(info, files):
    with open('.flakesignore') as f:
        ignores = [re.compile(stripeol(l)) for l in f]
    def accept(path):
        for pattern in ignores:
            if pattern.search(path) is not None:
                return False
        return True
    paths = [p for p in files.pypaths if accept(p)]
    if paths:
        subprocess.check_call([pathto('pyflakes')] + paths)

def pathto(executable):
    return os.path.join(os.path.dirname(sys.executable), executable)

def main():
    while not (os.path.exists('.hg') or os.path.exists('.svn') or os.path.exists('.git')):
        os.chdir('..')
    info = projectinfo.ProjectInfo(os.getcwd())
    files = Files()
    for check in (() if info['proprietary'] else (licheck,)) + (nlcheck, divcheck, execcheck, pyflakes):
        sys.stderr.write("%s: " % check.__name__)
        check(info, files)
        stderr('OK')
    sys.exit(subprocess.call([pathto('nosetests'), '--exe', '-v', '--with-xunit'] + files.testpaths() + sys.argv[1:]))

if '__main__' == __name__:
    main()
