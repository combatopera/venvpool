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

from .util import stderr
import re, os, sys, shutil

def removedir(path):
    if os.path.islink(path):
        os.remove(path)
    else:
        shutil.rmtree(path)

class Pattern:

    def __init__(self, regex, dironly):
        self.regex = re.compile(regex)
        self.dironly = dironly

    def accept(self, path, isdir):
        if self.dironly and not isdir:
            return False
        return self.regex.search(path) is not None

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.regex.pattern, self.dironly)

class HgStyle:

    name = '.hgignore'

    def pattern(self, line):
        return Pattern(line, False)

class GitStyle:

    name = '.gitignore'

    def pattern(self, line):
        if line.startswith('/'):
            anchor = '^'
            line = line[1:]
        else:
            anchor = '(?:^|/)'
        if line.endswith('/'):
            dironly = True
            line = line[:-1]
        else:
            dironly = False
        def repl(m):
            text = m.group()
            if '*' not in text:
                return re.escape(text)
            elif '*' == text:
                return '[^/]*'
            else:
                raise Exception("Unsupported glob: " % text)
        return Pattern("%s%s$" % (anchor, re.sub('[*]+|[^*]+', repl, line)), dironly)

def styleornone():
    for style in HgStyle, GitStyle:
        if os.path.exists(style.name):
            return style()

def main_gclean():
    roots = sys.argv[1:]
    while True:
        style = styleornone()
        if style is not None:
            stderr(style)
            break
        oldpwd = os.getcwd()
        os.chdir('..')
        if oldpwd == os.getcwd():
            raise Exception('No style found.')
        roots = [os.path.join(os.path.basename(oldpwd), root) for root in roots]
    patterns = []
    with open(style.name) as f:
        armed = False
        for line in f:
            line, = line.splitlines()
            if armed:
                patterns.append(style.pattern(line))
                stderr(patterns[-1])
            else:
                armed = '#gclean' == line
    def tryremovepath(path, isdir):
        path = os.path.normpath(path)
        for pattern in patterns:
            if pattern.accept(path, isdir):
                stderr(path)
                (removedir if isdir else os.remove)(path)
                break
    for root in (roots if roots else ['.']):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for name in dirnames:
                tryremovepath(os.path.join(dirpath, name), True)
            for name in sorted(filenames):
                tryremovepath(os.path.join(dirpath, name), False)
