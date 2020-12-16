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
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
import json, logging, os, shelve, subprocess, sys

log = logging.getLogger(__name__)
unzip = 'busybox', 'unzip', '-q', '-'
untar = 'tar', '-xz'

class PypiCache:

    def __init__(self, config, path):
        self.fetch = config.f
        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            os.makedirs(parent)
        self.d = shelve.open(path)

    def __enter__(self):
        return self

    def releases(self, cname):
        if not self.fetch and cname in self.d:
            return self.d[cname]
        with urlopen("https://pypi.org/pypi/%s/json" % cname) as f:
            self.d[cname] = releases = list(json.load(f)['releases'])
        return releases

    def requires_dist(self, cname, release):
        def keystr(major = sys.version_info.major):
            return "%s %s %s" % (cname, release, major)
        def savemulti():
            for major in 2, 3:
                self.d[keystr(major)] = requires
        majorkey = keystr()
        try:
            requires = self.d[majorkey]
        except KeyError:
            with urlopen("https://pypi.org/pypi/%s/%s/json" % (cname, release)) as f:
                data = json.load(f)
            requires = data['info']['requires_dist']
            if requires is not None:
                savemulti()
            else:
                sdists = [d for d in data['releases'][release] if 'sdist' == d['packagetype'] and not d['yanked']]
                if not sdists:
                    requires = Exception('No unyanked sdist.')
                    savemulti()
                else:
                    url = min(sdists, key = lambda d: d['size'])['url']
                    log.info("Execute: %s", url.split('/')[-1])
                    with TemporaryDirectory() as tempdir:
                        with subprocess.Popen(['curl', url], stdout = subprocess.PIPE) as curl:
                            subprocess.check_call(unzip if url.endswith('.zip') else untar, stdin = curl.stdout, cwd = tempdir)
                        if curl.returncode:
                            log.debug("Bad curl status: %s", curl.returncode) # Often trailing garbage ignored by unzip/untar.
                        d, = os.listdir(tempdir)
                        try:
                            requires = getsetupkwargs(os.path.join(tempdir, d, 'setup.py'), ['install_requires']).get('install_requires', [])
                        except Exception as e: # Do not catch KeyboardInterrupt!
                            requires = e
                    self.d[majorkey] = requires # Result is interpreter-specific.
        if isinstance(requires, BaseException):
            raise requires
        return requires

    def __exit__(self, *exc_info):
        self.d.close()
