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

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser
import importlib, os, sys

def load_entry_point(dist, group, name):
    for path in sys.path:
        if os.path.basename(path) == 'site-packages':
            with open(os.path.join(path, "%s.egg-link" % dist)) as f:
                line, = f.readline().splitlines()
            config = ConfigParser()
            config.read(os.path.join(line, "%s.egg-info" % dist.replace('-', '_'), 'entry_points.txt'))
            module, function = config.get(group, name).split(':')
            return getattr(importlib.import_module(module), function)
