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

from importlib import import_module
import os, sys

def _patch(modulename, setup):
    try:
        import_module(modulename).setup = setup
    except Exception as e:
        sys.stderr.write("Failed to patch %s: %s\n" % (modulename, e))

class Stack(list):

    def setup(self, **kwargs):
        self.append(kwargs)

def main():
    sys.argv.pop(0)
    path = sys.argv[0]
    sys.path.insert(0, os.path.dirname(path))
    stack = Stack()
    for m in 'distutils.core', 'setuptools':
        _patch(m, stack.setup)
    with open(path) as f:
        exec(f.read())
    setupkwargs, = stack
    sys.stdout.write(repr(setupkwargs))

if '__main__' == __name__:
    main()
