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

import os, re, sys

def stderr(obj):
    sys.stderr.write(str(obj))
    sys.stderr.write(os.linesep)

def stripeol(line):
    line, = line.splitlines()
    return line

class Excludes:

    def __init__(self, globs):
        def disjunction():
            sep = re.escape(os.sep)
            star = "[^%s]*" % sep
            def components():
                for word in glob.split('/'):
                    if '**' == word:
                        yield "(?:%s%s)*" % (star, sep)
                    else:
                        yield star.join(re.escape(part) for part in word.split('*'))
                        yield sep
            for glob in globs:
                concat = ''.join(components())
                assert concat.endswith(sep)
                yield concat[:-len(sep)]
        self.pattern = re.compile("^%s$" % '|'.join(disjunction()))

    def __contains__(self, relpath):
        return self.pattern.search(relpath) is not None
