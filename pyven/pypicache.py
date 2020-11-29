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

from lagoon.binary import busybox, tar
from tempfile import TemporaryDirectory
from urllib.request import urlopen
import json, os, shelve

class PypiCache:

    def __init__(self, path):
        self.d = shelve.open(path)

    def __enter__(self):
        return self

    def releases(self, cname):
        try:
            return self.d[cname]
        except KeyError:
            with urlopen("https://pypi.org/pypi/%s/json" % cname) as f:
                self.d[cname] = releases = list(json.load(f)['releases'])
            return releases

    def requires_dist(self, cname, release):
        from .checks import getsetupkwargs
        key = "%s==%s" % (cname, release)
        try:
            return self.d[key]
        except KeyError:
            with urlopen("https://pypi.org/pypi/%s/%s/json" % (cname, release)) as f:
                data = json.load(f)
            requires = data['info']['requires_dist']
            if requires is None:
                try:
                    url = min((d for d in data['releases'][release] if 'sdist' == d['packagetype'] and not d['yanked']), key = lambda d: d['size'])['url']
                except ValueError:
                    pass
                else:
                    with TemporaryDirectory() as tempdir, urlopen(url) as f:
                        if url.endswith('.zip'):
                            busybox.unzip._q._(input = f.read(), cwd = tempdir, stdout = None)
                        else:
                            tar._xz(input = f.read(), cwd = tempdir, stdout = None)
                        d, = os.listdir(tempdir)
                        requires = getsetupkwargs(os.path.join(tempdir, d, 'setup.py'))['install_requires']
            self.d[key] = requires
            return requires

    def __exit__(self, *exc_info):
        self.d.close()
