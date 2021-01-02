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

from argparse import ArgumentParser
import os

fieldlist = 'Name', 'Version'
fieldset = set(fieldlist)
egglinksuffix = '.egg-link'

def fastfreeze(venvpath):
    libpath = os.path.join(venvpath, 'lib')
    for name in os.listdir(libpath):
        site_packages = os.path.join(libpath, name, 'site-packages')
        if os.path.exists(site_packages):
            break
    info = {}
    for name in os.listdir(site_packages):
        if name.endswith('.dist-info'):
            with open(os.path.join(site_packages, name, 'METADATA')) as f:
                for line in f:
                    colon = line.index(':')
                    field = line[:line.index(':')]
                    if field in fieldset:
                        info[field] = line[colon + 1:].strip()
                        if len(fieldset) == len(info):
                            break
            yield [info[k] for k in fieldlist]
            info.clear()
        elif name.endswith(egglinksuffix):
            yield name[:-len(egglinksuffix)], '-e' # XXX: Which mangling of the name is this?

def main_fastfreeze():
    parser = ArgumentParser()
    parser.add_argument('venvpath')
    for name, version in fastfreeze(parser.parse_args().venvpath):
        if '-e' == version:
            print(version, name)
        else:
            print("%s==%s" % (name, version))
