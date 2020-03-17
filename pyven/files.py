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
from .util import stripeol
import subprocess, sys, os, xml.dom.minidom as dom, collections

class Files:

    reportpath = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'nosetests.xml')

    @staticmethod
    def _findfiles(walkpath, suffixes):
        prefixlen = len(walkpath + os.sep)
        for dirpath, dirnames, filenames in os.walk(walkpath):
            for name in sorted(filenames):
                for suffix in suffixes:
                    if name.endswith(suffix):
                        yield os.path.join(dirpath, name)[prefixlen:]
                        break # Next name.
            dirnames.sort()

    @classmethod
    def relpaths(cls, root, suffixes):
        paths = list(cls._findfiles(root, suffixes))
        with open(os.devnull) as devnull:
            if not subprocess.call(['hg', 'root'], stdout = devnull, stderr = devnull, cwd = root):
                badstatuses = set('IR ')
                for line in subprocess.Popen(['hg', 'st', '-A'] + paths, stdout = subprocess.PIPE, cwd = root).stdout:
                    line = stripeol(line).decode()
                    if line[0] not in badstatuses:
                        yield line[2:]
            else:
                p = subprocess.Popen(['git', 'check-ignore'] + paths, stdout = subprocess.PIPE, cwd = root)
                ignored = set(p.communicate()[0].decode().splitlines())
                assert p.wait() in [0, 1]
                for path in paths:
                    if path not in ignored:
                        yield path

    def __init__(self, root):
        self.allsrcpaths = [os.path.join(root, p) for p in self.relpaths(root, ['.py', '.py3', '.pyx', '.s', '.sh', '.h', '.cpp', '.cxx', '.arid'])]
        self.pypaths = [p for p in self.allsrcpaths if p.endswith('.py')]
        self.root = root

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
