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

from . import workingversion
from .projectinfo import ProjectInfo
from argparse import ArgumentParser
from aridimpl.model import Function, Number, Scalar, Text
from aridity import Repl
from pkg_resources import resource_filename
import os, subprocess, sys

def pyquote(context, resolvable):
    return Text(repr(resolvable.resolve(context).value))

def pipify(info, release):
    description, url = info.descriptionandurl() if release and not info['proprietary'] else [None, None]
    version = info.nextversion() if release else workingversion
    context = info.info.createchild()
    context['"',] = Function(pyquote)
    context['version',] = Scalar(version)
    context['description',] = Scalar(description)
    context['long_description',] = Text('long_description()' if release else repr(None))
    context['url',] = Scalar(url)
    if not release:
        context['author',] = Scalar(None)
    context['py_modules',] = Scalar(info.py_modules())
    context['install_requires',] = Scalar(info.allrequires() if release else info.remoterequires())
    context['scripts',] = Scalar(info.scripts())
    context['console_scripts',] = Scalar(info.console_scripts())
    context['universal',] = Number(int({2, 3} <= set(info['pyversions'])))
    with Repl(context) as repl:
        for name in 'setup.py', 'setup.cfg':
            repl.printf("redirect %s", os.path.abspath(os.path.join(info.projectdir, name)))
            repl.printf("< %s", resource_filename(__name__, name + '.aridt')) # XXX: Use stream?
    return version

def main_pipify():
    parser = ArgumentParser()
    parser.add_argument('-f')
    config = parser.parse_args()
    info = ProjectInfo.seek('.') if config.f is None else ProjectInfo('.', config.f)
    pipify(info, False)
    subprocess.check_call([sys.executable, 'setup.py', 'egg_info'], cwd = info.projectdir)
