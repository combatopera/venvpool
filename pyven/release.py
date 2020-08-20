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

from .checks import EveryVersion
from .initlogging import initlogging
from .pipify import pipify
from .projectinfo import ProjectInfo
from argparse import ArgumentParser
from lagoon.program import Program
from tempfile import TemporaryDirectory
import lagoon, logging, os, shutil, sys

log = logging.getLogger(__name__)
targetremote = 'origin'
distrelpath = 'dist'

def main_release():
    initlogging()
    parser = ArgumentParser()
    parser.add_argument('--upload', action = 'store_true')
    parser.add_argument('path', nargs = '?', default = '.')
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
        copydir = os.path.join(tempdir, os.path.basename(os.path.abspath(info.projectdir)))
        log.info("Copying project to: %s", copydir)
        shutil.copytree(info.projectdir, copydir)
        for relpath in release(config, git, ProjectInfo.seek(copydir)):
            log.info("Replace artifact: %s", relpath)
            destpath = os.path.join(info.projectdir, relpath)
            try:
                os.makedirs(os.path.dirname(destpath))
            except OSError:
                pass
            shutil.copy2(os.path.join(copydir, relpath), destpath)

def uploadableartifacts(artifactrelpaths):
    for p in artifactrelpaths:
        name = os.path.basename(p)
        if not name.endswith('.whl') or name.endswith('-any.whl'):
            yield p
        else:
            log.warning("Not uploadable: %s", p)

def release(config, srcgit, info):
    scrub = lagoon.git.clean._xdi.partial(cwd = info.projectdir, input = 'c', stdout = None)
    scrub()
    version = info.nextversion()
    pipify(info, version) # Test against releases, in theory.
    EveryVersion(info, False, False, []).allchecks()
    scrub()
    for dirpath, dirnames, filenames in os.walk(info.projectdir):
        for name in filenames:
            if name.startswith('test_') and name.endswith('.py'): # TODO LATER: Allow project to add globs to exclude.
                path = os.path.join(dirpath, name)
                log.debug("Delete: %s", path)
                os.remove(path)
    pipify(info, version)
    python = Program.text(sys.executable).partial(cwd = info.projectdir, stdout = None)
    python('setup.py', 'sdist', 'bdist_wheel')
    artifactrelpaths = [os.path.join(distrelpath, name) for name in os.listdir(os.path.join(info.projectdir, distrelpath))]
    if config.upload:
        srcgit.tag("v%s" % version, stdout = None)
        # TODO LATER: If tag succeeded but push fails, we're left with a bogus tag.
        srcgit.push.__tags(stdout = None) # XXX: Also update other remotes?
        python('-m', 'twine', 'upload', *uploadableartifacts(artifactrelpaths))
    else:
        log.warning('Upload skipped, use --upload to upload.')
    return artifactrelpaths
