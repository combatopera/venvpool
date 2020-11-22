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

from .universe import Universe
from pkg_resources import safe_name
from tempfile import NamedTemporaryFile
import logging, os, subprocess

log = logging.getLogger(__name__)

class Pip:

    envpatch = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')
    envimage = dict(os.environ, **envpatch)

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = self.envimage)

    def installeditable(self, infos):
        u = Universe(infos)
        specifiers = {}
        with NamedTemporaryFile('w') as f:
            for i in infos:
                f.write('package: %s\n' % i.config.name.replace(' ', ''))
                f.write('version: %s\n' % u.devcudfversion(i))
                deps = u.cudfdepends(i)
                if deps:
                    f.write('depends: %s\n' % ', '.join(deps))
                f.write('\n')
            f.write('request: \n') # Space is needed apparently!
            f.write('install: %s\n' % ', '.join(i.config.name.replace(' ', '') for i in infos))
            f.flush()
            subprocess.check_call(['cat', f.name])
            subprocess.check_call(['aspcud', '-V', '3', f.name])

        raise
        solution = ["%s%s" % entry for entry in specifiers.items()]
        log.debug("Install solution: %s", ' '.join(solution))
        self.pipinstall(solution)
        log.debug("Install editable: %s", ' '.join(safe_name(i.config.name) for i in infos))
        self.pipinstall(['--no-deps'] + sum((['-e', i.projectdir] for i in infos), []))

class Venv:

    def __init__(self, info, pyversion, prefix = ''):
        self.venvpath = os.path.join(info.projectdir, '.pyven', "%s%s" % (prefix, pyversion))
        if not os.path.exists(self.venvpath):
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, self.venvpath])

    def programpath(self, name):
        return os.path.join(self.venvpath, 'bin', name)

    def install(self, args):
        log.debug("Install: %s", ' '.join(args))
        if args:
            Pip(self.programpath('pip')).pipinstall(args)
