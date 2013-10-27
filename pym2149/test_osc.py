#!/usr/bin/env python

from __future__ import division
import unittest, lfsr, time
from osc import ToneOsc, NoiseOsc, EnvOsc
from nod import Block
from reg import Reg

class TestToneOsc(unittest.TestCase):

  def test_works(self):
    o = ToneOsc(8, Reg(3))
    v = o(Block(96)).tolist()
    self.assertEqual([1] * 24, v[:24])
    self.assertEqual([0] * 24, v[24:48])
    self.assertEqual([1] * 24, v[48:72])
    self.assertEqual([0] * 24, v[72:])
    v = o(Block(48)).tolist()
    self.assertEqual([1] * 24, v[:24])
    self.assertEqual([0] * 24, v[24:])

  def test_resume(self):
    o = ToneOsc(8, Reg(3))
    v = o(Block(25)).tolist()
    self.assertEqual([1] * 24, v[:24])
    self.assertEqual([0], v[24:])
    v = o(Block(24)).tolist()
    self.assertEqual([0] * 23, v[:23])
    self.assertEqual([1], v[23:])

  def test_carry(self):
    r = Reg(0x01)
    size = 3 * 8 + 1
    ref = list(ToneOsc(8, r)(Block(size)).buf)
    for n in xrange(size + 1):
      o = ToneOsc(8, r)
      v1 = list(o(Block(n)).buf)
      v2 = list(o(Block(size - n)).buf)
      self.assertEqual(ref, v1 + v2)

  def test_increaseperiodonboundary(self):
    r = Reg(0x01)
    o = ToneOsc(8, r)
    self.assertEqual([1] * 8 + [0] * 8, list(o(Block(16)).buf))
    r.value = 0x02
    self.assertEqual([0] * 8 + [1] * 16 + [0], list(o(Block(25)).buf))

  def test_decreaseperiodonboundary(self):
    r = Reg(0x02)
    o = ToneOsc(8, r)
    self.assertEqual([1] * 16 + [0] * 16 + [1] * 6, list(o(Block(38)).buf))
    r.value = 0x01
    self.assertEqual([1] * 2 + [0] * 8 + [1] * 8 + [0], list(o(Block(19)).buf))

  def test_performance(self):
    blockrate = 50
    blocksize = 2000000 // blockrate
    for p in 0x001, 0xfff:
      r = Reg(p)
      o = ToneOsc(8, r)
      start = time.time()
      for _ in xrange(blockrate):
        o(Block(blocksize))
      self.assertTrue(time.time() - start < .05)

class TestNoiseOsc(unittest.TestCase):

  def test_works(self):
    n = 100
    o = NoiseOsc(8, Reg(3))
    u = lfsr.Lfsr(*lfsr.ym2149nzdegrees)
    for _ in xrange(2):
      v = o(Block(48 * n)).tolist()
      for i in xrange(n):
        self.assertEqual([u()] * 48, v[i * 48:(i + 1) * 48])

  def test_carry(self):
    r = Reg(0x01)
    size = 17 * 16 + 1
    ref = list(NoiseOsc(8, r)(Block(size)).buf)
    for n in xrange(size + 1):
      o = NoiseOsc(8, r)
      v1 = list(o(Block(n)).buf)
      v2 = list(o(Block(size - n)).buf)
      self.assertEqual(ref, v1 + v2)

  def test_performance(self):
    blockrate = 50
    blocksize = 2000000 // blockrate
    for p in 0x01, 0x1f:
      r = Reg(p)
      o = NoiseOsc(8, r)
      start = time.time()
      for _ in xrange(blockrate):
        o(Block(blocksize))
      self.assertTrue(time.time() - start < .05)

class TestEnvOsc(unittest.TestCase):

  def test_values(self):
    v = EnvOsc.values0c
    self.assertEqual(1024, v.buf.shape[0])
    self.assertEqual(0, v.loop)
    self.assertEqual(range(32) + range(32), list(v.buf[:64]))
    v = EnvOsc.values08
    self.assertEqual(1024, v.buf.shape[0])
    self.assertEqual(0, v.loop)
    self.assertEqual(range(31, -1, -1) + range(31, -1, -1), list(v.buf[:64]))
    v = EnvOsc.values0e
    self.assertEqual(1024, v.buf.shape[0])
    self.assertEqual(0, v.loop)
    self.assertEqual(range(32) + range(31, -1, -1) + range(32), list(v.buf[:96]))
    v = EnvOsc.values0a
    self.assertEqual(1024, v.buf.shape[0])
    self.assertEqual(0, v.loop)
    self.assertEqual(range(31, -1, -1) + range(32) + range(31, -1, -1), list(v.buf[:96]))
    v = EnvOsc.values0f
    self.assertEqual(1032, v.buf.shape[0])
    self.assertEqual(32, v.loop)
    self.assertEqual(range(32) + [0] * 32, list(v.buf[:64]))
    v = EnvOsc.values0d
    self.assertEqual(1032, v.buf.shape[0])
    self.assertEqual(32, v.loop)
    self.assertEqual(range(32) + [31] * 32, list(v.buf[:64]))
    v = EnvOsc.values0b
    self.assertEqual(1032, v.buf.shape[0])
    self.assertEqual(32, v.loop)
    self.assertEqual(range(31, -1, -1) + [31] * 32, list(v.buf[:64]))
    v = EnvOsc.values09
    self.assertEqual(1032, v.buf.shape[0])
    self.assertEqual(32, v.loop)
    self.assertEqual(range(31, -1, -1) + [0] * 32, list(v.buf[:64]))

  def test_reset(self):
    shapereg = Reg(0x0c)
    periodreg = Reg(0x0001)
    o = EnvOsc(8, periodreg, shapereg)
    self.assertEqual(range(32) + range(16), list(o(Block(48 * 8)).buf[::8]))
    self.assertEqual(range(16, 32) + range(16), list(o(Block(32 * 8)).buf[::8]))
    shapereg.value = 0x0c
    self.assertEqual(range(32) + range(16), list(o(Block(48 * 8)).buf[::8]))

  def test_08(self):
    shapereg = Reg(0x08)
    periodreg = Reg(3)
    o = EnvOsc(8, periodreg, shapereg)
    for _ in xrange(2):
      v = o(Block(8 * 3 * 32)).tolist()
      for i in xrange(32):
        self.assertEqual([31 - i] * 24, v[i * 24:(i + 1) * 24])

  def test_09(self):
    for shape in xrange(0x04):
      o = EnvOsc(8, Reg(3), Reg(shape))
      v = o(Block(8 * 3 * 32)).tolist()
      for i in xrange(32):
        self.assertEqual([31 - i] * 24, v[i * 24:(i + 1) * 24])
      self.assertEqual([0] * (8 * 3 * 34), o(Block(8 * 3 * 34)).tolist())

  def test_0a(self):
    shapereg = Reg(0x0a)
    periodreg = Reg(3)
    o = EnvOsc(8, periodreg, shapereg)
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([31 - i] * 24, v[i * 24:(i + 1) * 24])
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([i] * 24, v[i * 24:(i + 1) * 24])
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([31 - i] * 24, v[i * 24:(i + 1) * 24])

  def test_0c(self):
    shapereg = Reg(0x0c)
    periodreg = Reg(3)
    o = EnvOsc(8, periodreg, shapereg)
    for _ in xrange(2):
      v = o(Block(8 * 3 * 32)).tolist()
      for i in xrange(32):
        self.assertEqual([i] * 24, v[i * 24:(i + 1) * 24])

  def test_0e(self):
    shapereg = Reg(0x0e)
    periodreg = Reg(3)
    o = EnvOsc(8,periodreg, shapereg)
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([i] * 24, v[i * 24:(i + 1) * 24])
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([31 - i] * 24, v[i * 24:(i + 1) * 24])
    v = o(Block(8 * 3 * 32)).tolist()
    for i in xrange(32):
      self.assertEqual([i] * 24, v[i * 24:(i + 1) * 24])

  def test_0f(self):
    for shape in xrange(0x04, 0x08):
      o = EnvOsc(8, Reg(3), Reg(shape))
      v = o(Block(8 * 3 * 32)).tolist()
      for i in xrange(32):
        self.assertEqual([i] * 24, v[i * 24:(i + 1) * 24])
      self.assertEqual([0] * (8 * 3 * 34), o(Block(8 * 3 * 34)).tolist())

if __name__ == '__main__':
  unittest.main()
