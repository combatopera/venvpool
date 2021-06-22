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

from .setuproot import getsetupkwargs
from .util import TemporaryDirectory
from tempfile import NamedTemporaryFile
from unittest import TestCase
import os, subprocess, sys

class TestSetupRoot(TestCase):

    def test_getsetupkwargs(self):
        with NamedTemporaryFile('w') as setup:
            setup.write('''from setuptools import setup
baz = 200
setup(foo = 'bar', bar = 100, baz = baz)''')
            setup.flush()
            self.assertEqual(dict(foo = 'bar', baz = 200), getsetupkwargs(setup.name, ['foo', 'baz', 'x']))

    def test_basenameonly(self):
        with TemporaryDirectory() as projectdir:
            with open(os.path.join(projectdir, 'setup.py'), 'w') as setup:
                setup.write('''from setuptools import setup
baz = 200
setup(foo = 'bar', bar = 100, baz = baz)''')
            self.assertEqual(dict(foo = 'bar', baz = 200), eval(subprocess.check_output([sys.executable, '-c', '''from pyven.setuproot import getsetupkwargs
import os, sys
os.chdir(*sys.argv[1:])
print(getsetupkwargs('setup.py', ['foo', 'baz', 'x']))''', projectdir], cwd = os.path.dirname(os.path.dirname(__file__)))))
