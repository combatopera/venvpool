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

from __future__ import with_statement
import hashlib, os, re, sys

gpltemplate = """# Copyright %(years)s %(author)s

# This file is part of %(name)s.
#
# %(name)s is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# %(name)s is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with %(name)s.  If not, see <http://www.gnu.org/licenses/>.
"""
intersection = '''# This file incorporates work covered by the following copyright and
# permission notice:
'''

def licheck(info, paths):
    if info.config.proprietary:
        sys.stderr.write('SKIP ')
        return
    sections = []
    for name in info.config.licenses:
        if sections:
            sections.append(intersection)
        if 'GPL' == name:
            sections.append(gpltemplate % {
                'years': ', '.join(str(y) for y in info.config.years),
                'author': info.config.author,
                'name': info.config.name,
            })
        elif 'MIT' == name:
            with open(info.mitpath()) as f:
                sections.append(''.join(('# ' if l.rstrip() else '#') + l for l in f))
        else:
            raise Exception(name)
    master = ''.join(s + '\n' for s in sections) # Check each section ends with 2 newlines.
    for path in paths:
        with open(path) as f:
            text = f.read()
        if text.startswith('#!'):
            for _ in range(2):
                text = text[text.index('\n') + 1:]
        if path.endswith('.s'):
            text = re.sub('^;', '#', text, flags = re.MULTILINE)
        elif path.endswith(('.h', '.cpp', '.cxx', '.gradle', '.java')):
            text = re.sub('^//', '#', text, flags = re.MULTILINE)
        elif path.endswith('.arid'):
            text = re.sub('^:', '#', text, flags = re.MULTILINE)
        text = text[:len(master)]
        if master != text:
            raise Exception(path)
    gplpath = os.path.join(info.projectdir, 'COPYING')
    md5 = hashlib.md5()
    with open(gplpath) as f:
        md5.update(f.read().encode('utf_8'))
    if 'd32239bcb673463ab874e80d47fae504' != md5.hexdigest():
        raise Exception(gplpath)
