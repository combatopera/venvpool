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

import logging, os, subprocess

log = logging.getLogger(__name__)

class Venv:

    def __init__(self, info, pyversion):
        self.venvpath = os.path.join(info.projectdir, '.pyven', str(pyversion))
        if not os.path.exists(self.venvpath):
            subprocess.check_call(['virtualenv', '-p', "python%s" % pyversion, self.venvpath])

    def programpath(self, name):
        return os.path.join(self.venvpath, 'bin', name)

    def install(self, args):
        log.debug("Install: %s", ' '.join(args))
        if args:
            subprocess.check_call([self.programpath('pip'), 'install'] + args)
