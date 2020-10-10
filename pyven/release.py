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

from . import targetremote
from .checks import EveryVersion
from .pipify import pipify
from .projectinfo import ProjectInfo
from .sourceinfo import SourceInfo
from .tryinstall import bgcontainer
from .util import initlogging
from argparse import ArgumentParser
from diapyr.util import enum, singleton
from itertools import chain
from lagoon.program import Program
from pkg_resources import resource_filename
from tempfile import TemporaryDirectory
import lagoon, logging, os, re, shutil, sys, sysconfig

log = logging.getLogger(__name__)
distrelpath = 'dist'

# TODO: There are more of these.
@enum(
    ['manylinux1_x86_64'],
    ['manylinux1_i686', True],
    ['manylinux2010_x86_64', False, True],
)
class Image:

    prefix = 'quay.io/pypa/'

    @singleton
    def pythonexe():
        impl = "cp%s" % sysconfig.get_config_var('py_version_nodot')
        return "/opt/python/%s-%s%s/bin/python" % (impl, impl, sys.abiflags)

    def __init__(self, plat, linux32 = False, prune = False):
        self.plat = plat
        self.entrypoint = ['linux32'] if linux32 else []
        self.prune = ['--prune'] if prune else []

    def makewheels(self, info): # TODO: This code would benefit from modern syntax.
        from lagoon import docker
        docker_print = docker.partial(stdout = None)
        log.info("Make wheels for platform: %s", self.plat)
        scripts = list(info.config.devel.scripts)
        packages = list(chain(info.config.devel.packages, ['sudo'] if scripts else []))
        # TODO LATER: It would be cool if the complete list could be expressed in aridity.
        compatibilities = list(chain(*(getattr(info.config.wheel.compatibilities, str(pyversion)) for pyversion in info.config.pyversions)))
        # TODO: Copy not mount so we can run containers in parallel.
        with bgcontainer('-v', "%s:/io" % info.projectdir, "%s%s" % (self.prefix, self.plat)) as container:
            def run(execargs, command):
                docker_print(*chain(['exec'], execargs, [container], self.entrypoint, command))
            if packages:
                run([], chain(['yum', 'install', '-y'], packages))
            for script in scripts:
                # TODO LATER: Run as ordinary sudo-capable user.
                dirpath = docker('exec', container, 'mktemp', '-d').rstrip() # No need to cleanup, will die with container.
                log.debug("In container dir %s run script: %s", dirpath, script)
                run(['-w', dirpath, '-t'], ['sh', '-c', script])
            docker_print.cp(resource_filename(__name__, 'patchpolicy.py'), "%s:/patchpolicy.py" % container)
            run([], [self.pythonexe, '/patchpolicy.py'])
            docker_print.cp(resource_filename(__name__, 'bdist.py'), "%s:/bdist.py" % container)
            run(['-u', "%s:%s" % (os.geteuid(), os.getegid()), '-w', '/io'], chain([self.pythonexe, '/bdist.py', '--plat', self.plat], self.prune, compatibilities))

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
    def acceptplatform(platform):
        return 'any' == platform or platform.startswith('manylinux')
    platformmatch = re.compile('-([^-]+)[.]whl$').search
    for p in artifactrelpaths:
        name = os.path.basename(p)
        if not name.endswith('.whl') or acceptplatform(platformmatch(name).group(1)):
            yield p
        else:
            log.debug("Not uploadable: %s", p)

def release(config, srcgit, info):
    scrub = lagoon.git.clean._xdi.partial(cwd = info.projectdir, input = 'c', stdout = None)
    scrub()
    version = info.nextversion()
    pipify(info, version)
    EveryVersion(info, False, False, []).allchecks()
    scrub()
    for dirpath, dirnames, filenames in os.walk(info.projectdir):
        for name in chain(filenames, dirnames):
            if name.startswith('test_'): # TODO LATER: Allow project to add globs to exclude.
                path = os.path.join(dirpath, name)
                log.debug("Delete: %s", path)
                (os.remove if name.endswith('.py') else shutil.rmtree)(path)
    python = Program.text(sys.executable).partial(cwd = info.projectdir, stdout = None)
    for m, f in (w.split(':') for w in info.config.warmups):
        python._c("from %s import %s; %s()" % (m, f, f))
    pipify(info, version)
    shutil.rmtree(os.path.join(info.projectdir, '.git'))
    setupcommands = []
    if SourceInfo(info.projectdir).extpaths:
        for image in Image.enum:
            image.makewheels(info)
    else:
        setupcommands.append('bdist_wheel')
    python('setup.py', *chain(setupcommands, ['sdist'])) # FIXME: Assumes release venv has Cython etc.
    artifactrelpaths = [os.path.join(distrelpath, name) for name in sorted(os.listdir(os.path.join(info.projectdir, distrelpath)))]
    if config.upload:
        srcgit.tag("v%s" % version, stdout = None)
        # TODO LATER: If tag succeeded but push fails, we're left with a bogus tag.
        srcgit.push.__tags(stdout = None) # XXX: Also update other remotes?
        python('-m', 'twine', 'upload', *uploadableartifacts(artifactrelpaths), env = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring'))
    else:
        log.warning("Upload skipped, use --upload to upload: %s", ' '.join(uploadableartifacts(artifactrelpaths)))
    return artifactrelpaths
