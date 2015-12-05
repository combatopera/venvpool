#!/usr/bin/env python

import sys, re, os

template="""# Copyright 2014 %(author)s

# This file is part of %(name)s.
#
# %(name)s is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# %(name)s is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with %(name)s.  If not, see <http://www.gnu.org/licenses/>.

""" # Check it ends with 2 newlines.

def main():
    infoname = 'project.info'
    projectpath = os.path.abspath(sys.argv[1])
    while True:
        parent = os.path.dirname(projectpath)
        if parent == projectpath:
            raise Exception(infoname)
        projectpath = parent
        infopath = os.path.join(projectpath, infoname)
        if os.path.exists(infopath):
            break
    info = {}
    execfile(infopath, info)
    master = template % info
    for path in sys.argv[1:]:
        f = open(path)
        try:
            text = f.read()
        finally:
            f.close()
        if text.startswith('#!'):
            for _ in xrange(2):
                text = text[text.index('\n') + 1:]
        text = text[:len(master)]
        if path.endswith('.s'):
            text = re.sub('^;', '#', text, flags = re.MULTILINE)
        if master != text:
            raise Exception(path)

if '__main__' == __name__:
    main()
