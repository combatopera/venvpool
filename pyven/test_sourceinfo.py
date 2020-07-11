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

from .sourceinfo import lazy
from unittest import TestCase

class TestLazy(TestCase):

    class Obj:

        k = 0

        def foo(self):
            return self.k

        def bar(self):
            return self.k

    def test_works(self):
        def init(o):
            o.k += 1
        obj = lazy(self.Obj, init, 'bar')
        self.assertEqual(0, obj.k)
        self.assertEqual(0, obj.foo())
        self.assertEqual(0, obj.k)
        self.assertEqual(1, obj.bar())
        self.assertEqual(1, obj.k)
        self.assertEqual(1, obj.bar())
        self.assertEqual(1, obj.k)
        for names in ['foo', 'bar'], ['bar', 'foo']:
            obj = lazy(self.Obj, init, *names)
            self.assertEqual(0, obj.k)
            self.assertEqual(1, obj.foo())
            self.assertEqual(1, obj.k)
            self.assertEqual(1, obj.foo())
            self.assertEqual(1, obj.k)
            self.assertEqual(1, obj.bar())
            self.assertEqual(1, obj.k)

    def test_works2(self):
        def init(v):
            v[:] = 0, 1, 2
        obj = lazy(list, init, '__iter__')
        self.assertEqual(0, len(obj))
        self.assertEqual((0, 1, 2), tuple(obj))
        self.assertEqual(3, len(obj))
        obj = lazy(list, init, '__getitem__')
        self.assertEqual((), tuple(obj))
        self.assertEqual(1, obj[1])
        self.assertEqual((0, 1, 2), tuple(obj))

    def test_lenisnotenough(self):
        def init(v):
            v[:] = 0, 1, 2
        obj = lazy(list, init, '__len__')
        n = 0
        for _ in obj:
            n += 1
        self.assertEqual(0, n)
        self.assertEqual(3, len(obj))
        for _ in obj:
            n += 1
        self.assertEqual(3, n)
