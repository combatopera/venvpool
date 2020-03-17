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

from .pipify import pipify
from .projectinfo import ProjectInfo
import os, sys, subprocess, shutil, argparse, logging

log = logging.getLogger(__name__)

def main_release():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('--upload', action = 'store_true')
    parser.add_argument('path', nargs = '?', type = os.path.abspath, default = os.getcwd())
    config = parser.parse_args()
    info = ProjectInfo(config.path)
    version = pipify(info, True)
    dist = os.path.join(info.projectdir, 'dist')
    if os.path.isdir(dist):
        shutil.rmtree(dist) # Remove any previous versions.
    subprocess.check_call([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd = info.projectdir)
    if config.upload:
        subprocess.check_call([sys.executable, '-m', 'twine', 'upload'] + [os.path.join(dist, name) for name in os.listdir(dist)])
        pipify(info, False)
        subprocess.check_call([sys.executable, 'setup.py', 'egg_info'], cwd = info.projectdir)
        subprocess.check_call(['git', 'tag', "v%s" % version])
        subprocess.check_call(['git', 'push', '--tags'])
    else:
        log.warning('Upload skipped, use --upload to upload.')
