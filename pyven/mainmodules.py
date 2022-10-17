# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022 Andrzej Cichocki

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

import ast, logging, os, sys

log = logging.getLogger(__name__)
extension = '.py'
prefix = 'main_'
scriptregex, = (r"^if\s+(?:__name__\s*==\s*{main}|{main}\s*==\s*__name__)\s*:\s*$".format(**locals()) for main in ['''(?:'__main__'|"__main__")'''])

def checkpath(projectdir, path):
    while True:
        path = os.path.dirname(path)
        if path == projectdir:
            return True
        if not os.path.exists(os.path.join(path, '__init__.py')):
            break

def commandornone(srcpath):
    name = os.path.basename(srcpath)
    name = os.path.basename(os.path.dirname(srcpath)) if '__init__.py' == name else name[:-len(extension)]
    if '-' not in name:
        return name.replace('_', '-')

def main():
    logging.basicConfig()
    paths = sys.argv[1:]
    projectdir = paths.pop(0)
    for relpath in paths:
        fullpath = os.path.join(projectdir, relpath)
        if not checkpath(projectdir, fullpath):
            continue
        with open(fullpath) as f:
            try:
                m = ast.parse(f.read())
            except SyntaxError:
                log.warning("Skip: %s" % relpath, exc_info = True)
                continue
        for obj in m.body:
            if isinstance(obj, ast.FunctionDef) and obj.name.startswith(prefix):
                command = obj.name[len(prefix):].replace('_', '-')
                print(dict(
                    command = command,
                    console_script = "%s=%s:%s" % (command, relpath[:-len(extension)].replace(os.sep, '.'), obj.name),
                    doc = ast.get_docstring(obj),
                ))

if ('__main__' == __name__):
    main()
