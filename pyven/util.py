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

from contextlib import contextmanager
from tempfile import mkdtemp
import logging, os, re, shutil, sys

cachedir = os.path.join(os.path.expanduser('~'), '.cache', 'pyven') # FIXME: Honour XDG_CACHE_HOME.
pyversiontags = {2: ['2'], 3: ['3.6', '3.7', '3.8', '3.9']}

def initlogging():
    logging.basicConfig(format = "%(asctime)s [%(levelname)s] %(message)s", level = logging.DEBUG)

def stderr(obj):
    sys.stderr.write(str(obj))
    sys.stderr.write(os.linesep)

def stripeol(line):
    line, = line.splitlines()
    return line

class Excludes:

    def __init__(self, globs):
        def disjunction():
            sep = re.escape(os.sep)
            star = "[^%s]*" % sep
            def components():
                for word in glob.split('/'):
                    if '**' == word:
                        yield "(?:%s%s)*" % (star, sep)
                    else:
                        yield star.join(re.escape(part) for part in word.split('*'))
                        yield sep
            for glob in globs:
                concat = ''.join(components())
                assert concat.endswith(sep)
                yield concat[:-len(sep)]
        self.pattern = re.compile("^%s$" % '|'.join(disjunction()))

    def __contains__(self, relpath):
        return self.pattern.search(relpath) is not None

class Path(str):

    @classmethod
    def seek(cls, dirpath, name):
        while True:
            path = cls(os.path.join(dirpath, name))
            if os.path.exists(path):
                path.parent = dirpath
                return path
            parent = os.path.join(dirpath, '..')
            if os.path.abspath(parent) == os.path.abspath(dirpath):
                break
            dirpath = parent

class ThreadPoolExecutor:

    def __enter__(self):
        return self

    def submit(self, f, *args, **kwargs):
        class Task:
            def result(self):
                return f(*args, **kwargs)
        return Task()

    def __exit__(self, *exc_info):
        pass

assert ThreadPoolExecutor
try:
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    pass

@contextmanager
def TemporaryDirectory():
    tempdir = mkdtemp()
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)

@contextmanager
def bgcontainer(*dockerrunargs):
    from lagoon import docker
    from lagoon.program import NOEOL
    container = docker.run._d[NOEOL](*dockerrunargs + ('sleep', 'inf'))
    try:
        yield container
    finally:
        docker.rm._f(container, stdout = None)

@contextmanager
def onerror(f):
    try:
        yield
    except:
        f()
        raise
