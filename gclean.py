#!/usr/bin/env python

# Copyright 2013, 2014, 2015, 2016 Andrzej Cichocki

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

import re, os, sys, shutil

def removedir(path):
    if os.path.islink(path):
        os.remove(path)
    else:
        shutil.rmtree(path)

class HgStyle:

    name = '.hgignore'

    def regex(self, line):
        return line

class GitStyle:

    name = '.gitignore'

    def regex(self, line):
        if line.startswith('/'):
            anchor = '^'
            line = line[1:]
        else:
            anchor = '(?:^|/)'
        def repl(m):
            text = m.group()
            if '*' not in text:
                return re.escape(text)
            elif '*' == text:
                return '[^/]*'
            else:
                raise Exception("Unsupported glob: " % text)
        return "%s%s$" % (anchor, re.sub('[*]+|[^*]+', repl, line))

def styleornone():
    for style in HgStyle, GitStyle:
        if os.path.exists(style.name):
            return style()

def main():
    roots = sys.argv[1:]
    while True:
        style = styleornone()
        if style is not None:
            print >> sys.stderr, style
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
                patterns.append(re.compile(style.regex(line)))
                print >> sys.stderr, '>', patterns[-1].pattern
            else:
                armed = '#gclean' == line
    def tryremovepath(path, remove):
        path = os.path.normpath(path)
        for pattern in patterns:
            if pattern.search(path) is not None:
                print >> sys.stderr, path
                remove(path)
                break
    for root in (roots if roots else ['.']):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for name in dirnames:
                tryremovepath(os.path.join(dirpath, name), removedir)
            for name in sorted(filenames):
                tryremovepath(os.path.join(dirpath, name), os.remove)

if '__main__' == __name__:
    main()
