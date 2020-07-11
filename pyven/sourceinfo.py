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

class SourceInfo:

    class PYXPath:

        dotpyx = '.pyx'

        def __init__(self, package, name, path):
            self.package = package
            self.name = name
            self.path = path

        def make_ext(self):
            g = {}
            with open(self.path + 'bld') as f: # Assume project root.
                exec(f.read(), g)
            return g['make_ext'](self.package + '.' + self.name[:-len(self.dotpyx)], self.path)

    def __init__(self, rootdir):
        import os, setuptools, subprocess
        self.packages = setuptools.find_packages(rootdir)
        def g():
            for package in self.packages:
                dirpath = package.replace('.', os.sep)
                for name in os.listdir(os.path.join(rootdir, dirpath)):
                    if name.endswith(self.PYXPath.dotpyx):
                        yield self.PYXPath(package, name, os.path.join(dirpath, name))
        pyxpaths = list(g())
        if pyxpaths and os.path.isdir(os.path.join(rootdir, '.git')): # We could be an unpacked sdist.
            check_ignore = subprocess.Popen(['git', 'check-ignore'] + [p.path for p in pyxpaths], cwd = rootdir, stdout = subprocess.PIPE)
            ignoredpaths = set(check_ignore.communicate()[0].decode().splitlines())
            assert check_ignore.wait() in [0, 1]
            self.pyxpaths = [path for path in pyxpaths if path.path not in ignoredpaths]
        else:
            self.pyxpaths = pyxpaths
