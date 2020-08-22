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
from tempfile import TemporaryDirectory
import logging, os, shutil, subprocess

log = logging.getLogger(__name__)
pythonroot = '/opt/python'
distdir = 'dist'

def main():
    logging.basicConfig(format = "<%(levelname)s> %(message)s", level = logging.DEBUG)
    parser = ArgumentParser()
    parser.add_argument('--plat', required = True)
    parser.add_argument('--prune', action = 'store_true')
    parser.add_argument('compatibilities', nargs = '+')
    args = parser.parse_args()
    with TemporaryDirectory() as holder:
        for compatibility in args.compatibilities:
            log.info("Make wheel(s) for implementation-ABI: %s", compatibility)
            subprocess.check_call([os.path.join(pythonroot, compatibility, 'bin', 'pip'), '--no-cache-dir', 'wheel', '--no-deps', '-w', holder, '.'])
            wheelpath, = (os.path.join(holder, n) for n in os.listdir(holder))
            subprocess.check_call(['auditwheel', 'repair', '--plat', args.plat, '-w', distdir, wheelpath])
            if not args.prune:
                shutil.copy2(wheelpath, distdir)
            os.remove(wheelpath)

if '__main__' == __name__:
    main()
