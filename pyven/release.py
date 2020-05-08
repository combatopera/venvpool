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

from .checks import everyversion
from .pipify import pipify
from .projectinfo import ProjectInfo
from argparse import ArgumentParser
from tempfile import TemporaryDirectory
import lagoon, logging, os, shutil, subprocess, sys

log = logging.getLogger(__name__)
targetremote = 'origin'

def main_release(): # TODO: Dockerise.
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    parser = ArgumentParser()
    parser.add_argument('--upload', action = 'store_true')
    parser.add_argument('path', nargs = '?', type = os.path.abspath, default = os.getcwd())
    config = parser.parse_args()
    info = ProjectInfo.seek(config.path)
    git = lagoon.git.partial(cwd = info.projectdir)
    if git.status.__porcelain():
        raise Exception('Uncommitted changes!')
    log.debug('No uncommitted changes.')
    remotename, _ = git.rev_parse.__abbrev_ref('@{u}').split('/')
    if targetremote != remotename:
        raise Exception("Current branch must track some %s branch." % targetremote)
    log.debug("Good remote: %s", remotename)
    with TemporaryDirectory() as tempdir:
        copydir = os.path.join(tempdir, os.path.basename(info.projectdir))
        log.info("Copying project to: %s", copydir)
        shutil.copytree(info.projectdir, copydir)
        release(config, git, ProjectInfo.seek(copydir), info.contextworkspace())

def release(config, srcgit, info, workspace):
    scrub = lagoon.git.clean._xdi.partial(cwd = info.projectdir, input = 'c', stdout = None)
    scrub()
    version = info.nextversion()
    pipify(info, version) # Test against releases, in theory.
    everyversion(info, workspace, []) # FIXME LATER: Dependencies of pyven interfere with those of project.
    scrub()
    for dirpath, dirnames, filenames in os.walk(info.projectdir):
        for name in filenames:
            if name.startswith('test_') and name.endswith('.py'):
                path = os.path.join(dirpath, name)
                log.debug("Delete: %s", path)
                os.remove(path)
    pipify(info, version)
    subprocess.check_call([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd = info.projectdir)
    if config.upload:
        srcgit.tag("v%s" % version, stdout = None)
        srcgit.push.__tags(stdout = None) # XXX: Also update other remotes?
        dist = os.path.join(info.projectdir, 'dist')
        subprocess.check_call([sys.executable, '-m', 'twine', 'upload'] + [os.path.join(dist, name) for name in os.listdir(dist)])
        # TODO: Copy artifacts back to source project.
    else:
        log.warning('Upload skipped, use --upload to upload.')
