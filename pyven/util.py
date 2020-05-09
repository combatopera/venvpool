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

import itertools, os, re, sys

def stderr(obj):
    sys.stderr.write(str(obj))
    sys.stderr.write(os.linesep)

def stripeol(line):
    line, = line.splitlines()
    return line

tomlbasicbadchars = re.compile('[%s]+' % re.escape(r'\"' + ''.join(chr(x) for x in itertools.chain(range(0x08 + 1), range(0x0A, 0x1F + 1), [0x7F]))))

def tomlquote(text): # TODO: Migrate to aridity.
    def repl(m):
        return ''.join(r"\u%04X" % ord(c) for c in m.group())
    return '"%s"' % tomlbasicbadchars.sub(repl, text)
