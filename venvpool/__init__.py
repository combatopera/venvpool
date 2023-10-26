# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022, 2023 Andrzej Cichocki

# This file is part of venvpool.
#
# venvpool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# venvpool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with venvpool.  If not, see <http://www.gnu.org/licenses/>.

import os, sys

class MainModule:

    letter = None

    def __init__(self):
        args = sys.argv
        if 1 < len(args):
            a = args[1]
            if 1 < len(a) and '-' == a[0]:
                self.letter = a[1]

    def shortcut(self, cls):
        if self.letter == cls.letter:
            sys.exit(cls.main())

    def end(self):
        Activate.main()

if ('__main__' == __name__): # Hide from scriptregex.
    _module = MainModule
else:
    class _module:
        def shortcut(self, cls):
            pass
        def end(self):
            pass
_module = _module()
propersubcommands = []

def _shortcut(cls):
    _module.shortcut(cls)
    propersubcommands.append(cls)
    return cls

def main():
    m = MainModule()
    for cls in propersubcommands:
        m.shortcut(cls)
    m.end()

def _decompress(paths):
    i = iter(paths)
    prefix = next(i)
    try:
        while True:
            yield prefix + next(i)
    except StopIteration:
        pass

@_shortcut
class Execute:

    help = 'augment interpreter environment and exec module for internal use only'
    letter = 'X'

    @classmethod
    def main(cls):
        import runpy # A few thousandths.
        assert '-X' == sys.argv.pop(1)
        sys.path[0] = bindir = os.path.dirname(sys.executable)
        try:
            envpath = os.environ['PATH']
        except KeyError:
            envpath = bindir
        else:
            envpath = bindir + os.pathsep + envpath
        os.environ['PATH'] = envpath
        sys.path[slice(*[cls._insertionpoint(sys.path)] * 2)] = _decompress(sys.argv.pop(1).split(os.pathsep))
        runpy.run_module(sys.argv.pop(1), run_name = '__main__', alter_sys = True)

    @staticmethod
    def _insertionpoint(v, suffix = os.sep + 'site-packages'):
        i = n = len(v)
        while not v[i - 1].endswith(suffix):
            i -= 1
            if not i:
                return n
        while i and v[i - 1].endswith(suffix):
            i -= 1
        return i

from collections import OrderedDict
from contextlib import contextmanager
from random import shuffle # XXX: Expensive?
from stat import S_IXUSR, S_IXGRP, S_IXOTH
from tempfile import mkdtemp, mkstemp
import errno, logging, operator, re, shutil # XXX: Still expensive?

class subprocess:

    def __getattr__(self, name):
        import subprocess # Up to a hundredth.
        return getattr(subprocess, name)

log = logging.getLogger(__name__)
chainrelpath = os.path.join('venvpool', 'chain.py')
dotpy = '.py'
executablebits = S_IXUSR | S_IXGRP | S_IXOTH
oserrors = {code: type(name, (OSError,), {}) for code, name in errno.errorcode.items()}
pooldir = os.path.join(os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache'), 'venvpool')
scriptregex, = (r"^if\s+(?:__name__\s*==\s*{main}|{main}\s*==\s*__name__)\s*:\s*$".format(**locals()) for main in ['''(?:'__main__'|"__main__")'''])
try:
    set_inheritable = os.set_inheritable
except AttributeError:
    from fcntl import fcntl, FD_CLOEXEC, F_GETFD, F_SETFD
    def set_inheritable(h, inherit):
        assert inherit
        fcntl(h, F_SETFD, fcntl(h, F_GETFD) & ~FD_CLOEXEC)
subprocess = subprocess()
userbin = os.path.join(os.path.expanduser('~'), '.local', 'bin')

def _osop(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except OSError as e:
        raise oserrors[e.errno](*e.args)

@contextmanager
def TemporaryDirectory():
    tempdir = mkdtemp()
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)

@contextmanager
def _onerror(f):
    try:
        yield
    except:
        f()
        raise

class Pip:

    envpatch = dict(PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring')

    def __init__(self, pippath):
        self.pippath = pippath

    def pipinstall(self, command):
        subprocess.check_call([self.pippath, 'install'] + command, env = dict(os.environ, **self.envpatch), stdout = sys.stderr)

def listorempty(d, xform = lambda p: p):
    try:
        names = _osop(os.listdir, d)
    except oserrors[errno.ENOENT]:
        return []
    return [xform(os.path.join(d, n)) for n in sorted(names)]

class LockStateException(Exception): pass

class ReadLock:

    def __init__(self, handle):
        self.handle = handle

    def unlock(self):
        try:
            _osop(os.close, self.handle)
        except oserrors[errno.EBADF]:
            raise LockStateException

def _idempotentunlink(path):
    try:
        _osop(os.remove, path)
        return True
    except oserrors[errno.ENOENT]:
        pass

def _chunkify(n, v):
    i = iter(v)
    while True:
        chunk = []
        for _ in range(n):
            try:
                x = next(i)
            except StopIteration:
                if chunk:
                    yield chunk
                return
            chunk.append(x)
        yield chunk

if '/' == os.sep:
    def _swept(readlocks):
        for chunk in _chunkify(1000, readlocks):
            # Check stderr instead of returncode for errors:
            stdout, stderr = subprocess.Popen(['lsof', '-t'] + chunk, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
            if not stderr and not stdout:
                for readlock in chunk:
                    if _idempotentunlink(readlock):
                        yield readlock
else:
    def _swept(readlocks): # TODO: Untested!
        for readlock in readlocks:
            try:
                if _idempotentunlink(readlock):
                    yield readlock
            except oserrors[errno.EACCES]:
                pass

def _compress(paths, splitchar = os.sep):
    if not paths:
        yield '-' # Avoid empty word in command line.
        return
    firstdiff = -1
    for firstdiff, chars in enumerate(zip(*paths)):
        if 1 != len(set(chars)):
            break
    else:
        firstdiff += 1
    while firstdiff and paths[0][firstdiff - 1] != splitchar:
        firstdiff -= 1
    yield paths[0][:firstdiff]
    for p in paths:
        yield p[firstdiff:]

class SharedDir(object):

    def __init__(self, dirpath):
        self.readlocks = os.path.join(dirpath, 'readlocks')

    def _sweep(self):
        paths = list(_compress(list(_swept(listorempty(self.readlocks)))))
        n = len(paths)
        if 2 == n:
            log.debug("Swept: %s%s", *paths)
        elif 2 < n:
            log.debug("Swept: %s{%s}", paths[0], ','.join(paths[1:]))

    def trywritelock(self):
        self._sweep()
        try:
            _osop(os.rmdir, self.readlocks)
            return True
        except (oserrors[errno.ENOENT], oserrors[errno.ENOTEMPTY]):
            pass

    def createortrywritelock(self):
        try:
            _osop(os.mkdir, os.path.dirname(self.readlocks))
            return True
        except oserrors[errno.EEXIST]:
            return self.trywritelock()

    def writeunlock(self):
        try:
            _osop(os.mkdir, self.readlocks)
        except oserrors[errno.EEXIST]:
            raise LockStateException

    def tryreadlock(self):
        try:
            h = _osop(mkstemp, dir = self.readlocks, prefix = 'lock')[0]
            set_inheritable(h, True)
            return ReadLock(h)
        except oserrors[errno.ENOENT]:
            pass

def safe_name(name):
    return re.sub('[^A-Za-z0-9.]+', '-', name)

def to_filename(name):
    return name.replace('-', '_')

class Venv(SharedDir):

    @staticmethod
    def _safewhich(name):
        poolprefix = pooldir + os.sep
        for bindir in os.environ['PATH'].split(os.pathsep):
            if bindir.startswith(poolprefix) or not os.path.isabs(bindir): # XXX: Also exclude other venvs?
                log.debug("Ignore bin directory: %s", bindir)
            else:
                path = os.path.join(bindir, name)
                if os.path.exists(path):
                    return path

    @property
    def site_packages(self):
        libpath = os.path.join(self.venvpath, 'lib')
        pyname, = (n for n in os.listdir(libpath) if n.startswith('python'))
        return os.path.join(libpath, pyname, 'site-packages')

    def __init__(self, venvpath):
        super(Venv, self).__init__(venvpath)
        self.venvpath = venvpath

    def create(self, pyversion):
        def isolated(*command):
            subprocess.check_call(command, cwd = tempdir, stdout = sys.stderr)
        executable = self._safewhich("python%s" % pyversion)
        absvenvpath = os.path.abspath(self.venvpath) # XXX: Safe when venvpath has symlinks?
        with TemporaryDirectory() as tempdir:
            if pyversion < 3:
                isolated('virtualenv', '-p', executable, absvenvpath)
            else:
                isolated(executable, '-m', 'venv', absvenvpath)
                isolated(os.path.join(absvenvpath, 'bin', 'pip'), 'install', '--upgrade', 'pip', 'setuptools', 'wheel')
        chainpath = os.path.join(self.site_packages, chainrelpath)
        os.mkdir(os.path.dirname(chainpath))
        with open(chainpath, 'w') as f:
            f.write('''import os, sys
v = [os.path.join(os.path.dirname(sys.executable), sys.argv[1])] + sys.argv[2:]
os.execv(v[0], v)
''')

    def delete(self, label = 'transient'):
        log.debug("Delete %s venv: %s", label, self.venvpath)
        shutil.rmtree(self.venvpath)

    def programpath(self, name):
        return os.path.join(self.venvpath, 'bin', name)

    def install(self, args):
        log.debug("Install: %s", ' '.join(args))
        if args:
            Pip(self.programpath('pip')).pipinstall(args)

    def compatible(self, installdeps):
        for r in installdeps.pypireqs:
            version = self._reqversionornone(r.namepart)
            if version is None or not r.acceptversion(version):
                return
        log.debug("Found compatible venv: %s", self.venvpath)
        return True

    def _reqversionornone(self, name):
        patterns = [re.compile(format % nameregex) for nameregex in [re.escape(to_filename(safe_name(name)).lower())] for format in [
            "^%s-(.+)[.]dist-info$",
            "^%s-([^-]+).*[.]egg-info$"]]
        for lowername in (n.lower() for n in os.listdir(self.site_packages)):
            for p in patterns:
                m = p.search(lowername)
                if m is not None:
                    return m.group(1)

    def run(self, mode, localreqs, module, scriptargs, **kwargs):
        argv = [os.path.join(self.venvpath, 'bin', 'python'), _stripc(__file__), '-X', os.pathsep.join(_compress(localreqs)), module] + scriptargs
        if 'call' == mode:
            return subprocess.call(argv, **kwargs)
        if 'check_call' == mode:
            return subprocess.check_call(argv, **kwargs)
        if 'check_output' == mode:
            return subprocess.check_output(argv, **kwargs)
        if 'exec' == mode:
            os.execv(argv[0], argv, **kwargs)
        raise ValueError(mode)

def _stripc(path):
    return path[:-1] if 'c' == path[-1] else path

class Pool:

    @property
    def versiondir(self):
        return os.path.join(pooldir, str(self.pyversion))

    def __init__(self, pyversion):
        self.readonlyortransient = {
            False: self.readonly,
            True: self._transient,
        }
        self.readonlyorreadwrite = {
            False: self.readonly,
            True: self.readwrite,
        }
        self.pyversion = pyversion

    def _newvenv(self, installdeps):
        log.info('Create new venv.')
        try:
            _osop(os.makedirs, self.versiondir)
        except oserrors[errno.EEXIST]:
            pass
        venv = Venv(mkdtemp(dir = self.versiondir, prefix = 'venv'))
        with _onerror(venv.delete):
            venv.create(self.pyversion)
            installdeps.invoke(venv)
            assert venv.compatible(installdeps) # Bug if not.
            return venv

    def _lockcompatiblevenv(self, trylock, installdeps):
        venvs = listorempty(self.versiondir, Venv)
        shuffle(venvs)
        for venv in venvs:
            lock = trylock(venv)
            if lock is not None:
                with _onerror(lock.unlock):
                    if venv.compatible(installdeps): # TODO: Upgrade venv if it has a subset.
                        return venv, lock
                lock.unlock()

    @contextmanager
    def _transient(self, installdeps):
        venv = self._newvenv(installdeps)
        try:
            yield venv
        finally:
            venv.delete()

    @contextmanager
    def readonly(self, installdeps):
        while True:
            t = self._lockcompatiblevenv(Venv.tryreadlock, installdeps)
            if t is not None:
                venv, readlock = t
                break
            venv = self._newvenv(installdeps)
            # XXX: Would it be possible to atomically convert write lock to read lock?
            venv.writeunlock()
            readlock = venv.tryreadlock()
            if readlock is not None:
                break
        try:
            yield venv
        finally:
            readlock.unlock()

    @contextmanager
    def readwrite(self, installdeps):
        def trywritelock(venv):
            if venv.trywritelock():
                class WriteLock:
                    def unlock(self):
                        venv.writeunlock()
                return WriteLock()
        t = self._lockcompatiblevenv(trywritelock, installdeps)
        if t is None:
            venv = self._newvenv(installdeps)
        else:
            venv = t[0]
            with _onerror(venv.writeunlock):
                for dirpath, dirnames, filenames in os.walk(venv.venvpath):
                    for name in filenames:
                        p = os.path.join(dirpath, name)
                        if 1 != os.stat(p).st_nlink:
                            h, q = mkstemp(dir = dirpath)
                            os.close(h)
                            shutil.copy2(p, q)
                            os.remove(p) # Cross-platform.
                            os.rename(q, p)
        try:
            yield venv
        finally:
            venv.writeunlock()

class FastReq:

    class Version:

        def __init__(self, operator, splitversion):
            self.operator = operator
            self.splitversion = splitversion

        def accept(self, splitversion):
            def pad(v):
                return v + [0] * (n - len(v))
            versions = [splitversion, self.splitversion]
            n = max(map(len, versions))
            return self.operator(*map(pad, versions))

    class DevSegment:

        def __init__(self, n):
            self.n = n

    @classmethod
    def _splitversion(cls, versionstr, devprefix = 'dev'):
        return [cls.DevSegment(int(k[len(devprefix):])) if k.startswith(devprefix) else int(k) for k in versionstr.split('.')]

    s = r'\s*'
    nameregex = '[A-Za-z0-9._-]+' # Slightly more lenient than PEP 508.
    extras = r"\[{s}(?:{nameregex}{s}(?:,{s}{nameregex}{s})*)?]".format(**locals())
    version = "(<|<=|!=|==|>=|>){s}([0-9.]+(?:[.]dev[0-9]+)?)".format(**locals()) # Subset of features.
    versionregex = "^{s}{version}{s}$".format(**locals())
    getregex = "^{s}({nameregex}){s}({extras}{s})?({version}{s}(?:,{s}{version}{s})*)?$".format(**locals())
    skipregex = "^{s}(?:#|$)".format(**locals())
    del s, extras, version
    operators = {
        '<': operator.lt,
        '<=': operator.le,
        '!=': operator.ne,
        '==': operator.eq,
        '>=': operator.ge,
        '>': operator.gt,
    }

    @classmethod
    def parselines(cls, lines):
        def g():
            for line in lines:
                if re.search(cls.skipregex, line) is not None:
                    continue
                namepart, extras, versionspec = re.search(cls.getregex, line).groups()[:3]
                extras = () if extras is None else tuple(sorted(set(re.findall(cls.nameregex, extras)))) # TODO LATER: Normalisation.
                versions = []
                reqstrversions = []
                if versionspec is not None:
                    for onestr in versionspec.split(','):
                        operatorstr, versionstr = re.search(cls.versionregex, onestr).groups()
                        versions.append(cls.Version(cls.operators[operatorstr], cls._splitversion(versionstr)))
                        reqstrversions.append(operatorstr + versionstr)
                yield cls(namepart, extras, versions, namepart + ("[%s]" % ','.join(extras) if extras else '') + ','.join(sorted(reqstrversions)))
        return list(g())

    def __init__(self, namepart, extras, versions, reqstr):
        self.namepart = namepart
        self.extras = extras
        self.versions = versions
        self.reqstr = reqstr

    def acceptversion(self, versionstr):
        splitversion = self._splitversion(versionstr)
        return all(v.accept(splitversion) for v in self.versions)

class ParsedRequires:

    parselines = staticmethod(FastReq.parselines)

    def __init__(self, requires):
        self.pypireqs = self.parselines(requires)

    def invoke(self, venv):
        venv.install([r.reqstr for r in self.pypireqs])

    def poplocalreqs(self, workspace):
        local = OrderedDict()
        reqs = list(self.pypireqs)
        del self.pypireqs[:]
        while reqs:
            nextreqs = []
            for req in reqs:
                projectdir = os.path.join(workspace, req.namepart)
                if projectdir not in local:
                    if os.path.exists(projectdir):
                        requirementslines = _getrequirementslinesornone(projectdir, req.extras)
                        if requirementslines is None:
                            raise NoRequirementsFoundException("%s[%s]" % (projectdir, ','.join(req.extras)))
                        nextreqs.extend(self.parselines(requirementslines))
                        local[projectdir] = None
                    else:
                        self.pypireqs.append(req)
            reqs = nextreqs
        return list(local)

def _getrequirementslinesornone(projectdir, extras):
    def linesornone(acceptnull, *names):
        path = os.path.join(projectdir, *names)
        if os.path.exists(path):
            log.debug("Found requirements: %s", path)
            with open(path) as f:
                return f.read().splitlines()
        if acceptnull:
            log.debug("Null requirements: %s", path)
            return []
    if extras:
        log.warning("Ignore extras %s in: %s", ','.join(extras), projectdir) # TODO: Find extra requirements as well.
    v = linesornone(False, 'requirements.txt')
    if v is not None:
        return v
    names = [name for name in os.listdir(projectdir) if name.endswith('.egg-info')]
    if names:
        name, = names # XXX: Could there legitimately be multiple?
        return linesornone(True, name, 'requires.txt')

def initlogging():
    logging.basicConfig(format = "%(asctime)s %(levelname)s %(message)s", level = logging.DEBUG)

class ParserCommand:

    @classmethod
    def main(cls):
        from argparse import ArgumentParser # Two or three hundredths.
        initlogging()
        parser = ArgumentParser(description = cls.help)
        if cls.letter is not None:
            parser.add_argument('-' + cls.letter, action = 'store_true', help = 'select this subcommand')
        cls.initparser(parser)
        parser.add_argument('-v', action = 'store_true', help = 'show debug logging')
        args = parser.parse_args()
        if cls.letter is not None:
            assert getattr(args, cls.letter)
        if not args.v:
            logging.getLogger().setLevel(logging.INFO)
        cls.mainimpl(args)

class NoRequirementsFoundException(Exception): pass

def _findrequirements(projectdir):
    while True:
        requirementslines = _getrequirementslinesornone(projectdir, ())
        if requirementslines is not None:
            return projectdir, requirementslines
        parent = os.path.dirname(projectdir)
        if parent == projectdir:
            raise NoRequirementsFoundException
        projectdir = parent

@_shortcut
class Launch(ParserCommand):

    help = 'launch a script with the interpreter and requirements it needs'
    letter = 'L'

    @staticmethod
    def initparser(parser):
        parser.add_argument('--req', help = 'use the given requirement specifier only')
        parser.add_argument('scriptpath', help = 'should be preceded by a -- arg')
        parser.add_argument('scriptarg', nargs = '*', help = 'arguments for scriptpath')

    @classmethod
    def mainimpl(cls, args):
        scriptpath = args.scriptpath
        assert scriptpath.endswith(dotpy)
        reqstr = args.req
        if reqstr is None:
            scriptpath = os.path.abspath(scriptpath) # XXX: Is abspath safe when scriptpath has symlinks?
            projectdir, requirementslines = _findrequirements(os.path.dirname(scriptpath))
            installdeps = ParsedRequires(requirementslines)
            localreqs = installdeps.poplocalreqs(os.path.normpath(os.path.join(projectdir, '..')))
            localreqs.insert(0, projectdir)
            module = os.path.relpath(scriptpath[:-len(dotpy)], projectdir).replace(os.sep, '.')
        else:
            installdeps = ParsedRequires([reqstr])
            localreqs = []
            module = scriptpath[:-len(dotpy)].replace(os.sep, '.')
        with Pool(sys.version_info.major).readonly(installdeps) as venv: # TODO: Likely to be major 2 when launching manually.
            venv.run('exec', localreqs, module, args.scriptarg)

class Activate(ParserCommand):

    help = 'create and maintain wrapper scripts'
    letter = None

    @staticmethod
    def initparser(parser):
        group = parser.add_mutually_exclusive_group()
        for cls in propersubcommands:
            group.add_argument('-' + cls.letter, action = 'store_true', help = 'subcommand to ' + cls.help)
        parser.add_argument('-f', action = 'store_true', help = 'overwrite existing scripts')
        parser.add_argument('projectdir', nargs = '*', default = ['.'], help = 'projects to search for runnable modules')

    @classmethod
    def mainimpl(cls, args):
        for projectdir in args.projectdir:
            try:
                cls._scan(_findrequirements(os.path.realpath(projectdir))[0], 3, args.f) # XXX: Always 3?
            except NoRequirementsFoundException:
                log.exception("Skip: %s", projectdir)

    @staticmethod
    def _srcpaths(rootdir):
        for dirpath, dirnames, filenames in os.walk(rootdir):
            for name in filenames:
                if name.endswith(dotpy):
                    path = os.path.join(dirpath, name)
                    with open(path) as f:
                        if re.search(scriptregex, f.read(), re.MULTILINE) is not None:
                            yield path

    @classmethod
    def _scan(cls, projectdir, pyversion, force):
        for srcpath in cls._srcpaths(projectdir):
            if not checkpath(projectdir, srcpath):
                log.debug("Not a project source file: %s", srcpath)
                continue
            command = commandornone(srcpath)
            if command is None:
                log.debug("Bad source name: %s", srcpath)
                continue
            cls.install(force, command, pyversion, None, srcpath)

    @staticmethod
    def install(force, command, pyversion, reqstrornone, *words):
        def allwords():
            if reqstrornone is not None:
                yield '--req'
                yield reqstrornone
            yield '--'
            for w in words:
                yield w
        def identical():
            mode = os.stat(scriptpath).st_mode
            if mode | executablebits == mode:
                with open(scriptpath) as f:
                    return f.read() == text
        wordsrepr = ', '.join(map(repr, allwords()))
        venvpoolpath = _stripc(os.path.realpath(__file__))
        text = """#!/usr/bin/env python{pyversion}
import sys
sys.argv[1:1] = '-L', {wordsrepr}
__file__ = {venvpoolpath!r}
with open(__file__) as f: venvpoolsrc = f.read()
del sys, f
exec(venvpoolsrc)
""".format(**locals())
        scriptpath = os.path.join(userbin, command) # TODO: Warn if shadowed.
        if os.path.exists(scriptpath):
            if identical():
                log.debug("Identical: %s", scriptpath)
                return
            if not force:
                log.info("Exists: %s", scriptpath)
                return
            log.info("Overwrite: %s", scriptpath)
        else:
            log.info("Create: %s", scriptpath)
        with open(scriptpath, 'w') as f:
            f.write(text)
        os.chmod(scriptpath, os.stat(scriptpath).st_mode | executablebits)

def checkpath(projectdir, path):
    while True:
        path = os.path.dirname(path)
        if path == projectdir:
            return True
        if not os.path.exists(os.path.join(path, '__init__.py')): # XXX: What about namespace packages?
            break

def commandornone(srcpath):
    name = os.path.basename(srcpath)
    name = os.path.basename(os.path.dirname(srcpath)) if '__init__.py' == name else name[:-len(dotpy)]
    if '-' not in name:
        return name.replace('_', '-')

@_shortcut
class Compact(ParserCommand):

    help = 'compact the pool of venvs'
    letter = 'C'

    @staticmethod
    def initparser(parser):
        pass

    @classmethod
    def mainimpl(cls, args): # XXX: Combine venvs with orthogonal dependencies?
        venvtofreeze = {}
        try:
            for versiondir in listorempty(pooldir):
                for venv in listorempty(versiondir, Venv):
                    if venv.trywritelock():
                        venvtofreeze[venv] = set(subprocess.check_output([venv.programpath('pip'), 'freeze'], universal_newlines = True).splitlines())
                    else:
                        log.debug("Busy: %s", venv.venvpath)
            log.debug('Find redundant venvs.')
            while True:
                venv = cls._redundantvenv(venvtofreeze)
                if venv is None:
                    break
                venv.delete('redundant')
                venvtofreeze.pop(venv)
            cls._compactvenvs([l.venvpath for l in venvtofreeze])
        finally:
            for l in venvtofreeze:
                l.writeunlock()

    @staticmethod
    def _redundantvenv(venvtofreeze):
        for venv, freeze in venvtofreeze.items():
            for othervenv, otherfreeze in venvtofreeze.items():
                if venv != othervenv and os.path.dirname(venv.venvpath) == os.path.dirname(othervenv.venvpath) and freeze <= otherfreeze:
                    return venv

    @staticmethod
    def _compactvenvs(venvpaths):
        log.info("Compact %s venvs.", len(venvpaths))
        if venvpaths:
            subprocess.check_call(['jdupes', '-Lrq'] + venvpaths)
        log.info('Compaction complete.')

@_shortcut
class ConsoleScripts(ParserCommand):

    help = 'activate all console scripts of the given requirement specifier'
    letter = 'S'

    @staticmethod
    def initparser(parser):
        parser.add_argument('-f', action = 'store_true', help = 'overwrite existing scripts')
        parser.add_argument('spec', help = 'a requirement specifier')

    @classmethod
    def mainimpl(cls, args):
        from inspect import getsource # About two hundredths.
        spec, = FastReq.parselines([args.spec])
        pyversion = 3
        with TemporaryDirectory() as tempdir:
            with open(os.path.join(tempdir, 'list.py'), 'w') as f:
                f.write("class C:\n%sC.%s(%r)\n" % (getsource(cls._commands), cls._commands.__name__, spec.namepart))
            with Pool(pyversion).readonly(ParsedRequires(['importlib-metadata', spec.reqstr])) as venv:
                names = set(venv.run('check_output', [tempdir], 'list', [], universal_newlines = True).splitlines())
        for name in names:
            Activate.install(args.f, name, pyversion, spec.reqstr, chainrelpath, name)

    @staticmethod
    def _commands(distname):
        from importlib_metadata import distribution, files
        for ep in distribution(distname).entry_points:
            if 'console_scripts' == ep.group:
                print(ep.name)
        for p in files(distname):
            t = p.parts
            if 5 == len(t) and ('..', '..', '..', 'bin') == t[:4]:
                print(t[4])

_module.end()
