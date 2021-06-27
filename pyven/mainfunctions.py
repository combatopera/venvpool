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

import ast, logging, os, sys

log = logging.getLogger(__name__)
prefix = 'main_'
extension = '.py'

def main():
    logging.basicConfig()
    paths = sys.argv[1:]
    projectdir = paths.pop(0)
    for path in paths:
        with open(os.path.join(projectdir, path)) as f:
            try:
                m = ast.parse(f.read())
            except SyntaxError:
                log.warning("Skip: %s" % path, exc_info = True)
                continue
        for obj in m.body:
            if isinstance(obj, ast.FunctionDef) and obj.name.startswith(prefix):
                name = obj.name[len(prefix):].replace('_', '-')
                print(dict(
                    name = name,
                    console_script = "%s=%s:%s" % (name, path[:-len(extension)].replace(os.sep, '.'), obj.name),
                    doc = ast.get_docstring(obj),
                ))

if '__main__' == __name__:
    main()
