from __future__ import division
import lfsr, numpy as np, itertools
from nod import Node

class OscNode(Node):

  oscdtype = np.uint8 # Slightly faster than plain old int.

  def __init__(self, periodreg):
    Node.__init__(self, self.oscdtype)
    self.valueindex = 0
    self.periodreg = periodreg

  def getvalue(self, n = 1):
    self.warp(n - 1)
    self.lastvalue = self.values.buf[self.valueindex]
    self.warp(1)
    return self.lastvalue

  def warp(self, n):
    self.valueindex += n
    size = self.values.buf.shape[0]
    while self.valueindex >= size:
      self.valueindex = self.values.loop + self.valueindex - size

class Values:

  def __init__(self, g, loop = 0):
    self.buf = np.fromiter(g, OscNode.oscdtype)
    self.loop = loop

class ToneOsc(OscNode):

  scaleofstep = 16 // 2
  values = Values(1 - (i & 1) for i in xrange(1000))

  def __init__(self, periodreg):
    OscNode.__init__(self, periodreg)
    self.progress = self.scaleofstep * 0xfff # Matching biggest possible stepsize.

  def callimpl(self):
    self.stepsize = self.scaleofstep * self.periodreg.value
    # If progress beats the new stepsize, we terminate right away:
    cursor = min(self.block.framecount, max(0, self.stepsize - self.progress))
    cursor and self.blockbuf.fillpart(0, cursor, self.lastvalue)
    self.progress = min(self.progress + cursor, self.stepsize)
    if cursor == self.block.framecount:
      return
    fullsteps = (self.block.framecount - cursor) // self.stepsize
    if self.blockbuf.putringops(self.values.buf, self.valueindex, fullsteps) * self.stepsize < fullsteps:
      for i in xrange(self.stepsize):
        self.blockbuf.putring(cursor + i, self.stepsize, self.values.buf, self.valueindex, fullsteps)
      self.getvalue(fullsteps)
      cursor += fullsteps * self.stepsize
    else:
      for _ in xrange(fullsteps):
        self.blockbuf.fillpart(cursor, cursor + self.stepsize, self.getvalue())
        cursor += self.stepsize
    if cursor == self.block.framecount:
      return
    self.blockbuf.fillpart(cursor, self.block.framecount, self.getvalue())
    self.progress = self.block.framecount - cursor

class NoiseOsc(OscNode):

  scaleofstep = 16 # One step per scale results in authentic spectrum, see qnoispec.
  values = Values(lfsr.Lfsr(*lfsr.ym2149nzdegrees))

  def __init__(self, periodreg):
    OscNode.__init__(self, periodreg)
    self.progress = self.stepsize = 0

  def callimpl(self):
    cursor = min(self.block.framecount, self.stepsize - self.progress)
    cursor and self.blockbuf.fillpart(0, cursor, self.lastvalue)
    self.progress += cursor
    if cursor == self.block.framecount:
      return
    self.stepsize = self.scaleofstep * self.periodreg.value
    fullsteps = (self.block.framecount - cursor) // self.stepsize
    if self.blockbuf.putringops(self.values.buf, self.valueindex, fullsteps) * self.stepsize < fullsteps:
      for i in xrange(self.stepsize):
        self.blockbuf.putring(cursor + i, self.stepsize, self.values.buf, self.valueindex, fullsteps)
      self.getvalue(fullsteps)
      cursor += fullsteps * self.stepsize
    else:
      for _ in xrange(fullsteps):
        self.blockbuf.fillpart(cursor, cursor + self.stepsize, self.getvalue())
        cursor += self.stepsize
    if cursor == self.block.framecount:
      self.progress = self.stepsize # Necessary in case stepsize changed.
      return
    self.blockbuf.fillpart(cursor, self.block.framecount, self.getvalue())
    self.progress = self.block.framecount - cursor

def cycle(v, minsize): # Unlike itertools version, we assume v can be iterated more than once.
  for _ in xrange((minsize + len(v) - 1) // len(v)):
    for x in v:
      yield x

class EnvOsc(OscNode):

  steps = 32
  scaleofstep = 256 // steps
  values0c = Values(cycle(range(steps), 1000))
  values08 = Values(cycle(range(steps - 1, -1, -1), 1000))
  values0e = Values(cycle(range(steps) + range(steps - 1, -1, -1), 1000))
  values0a = Values(cycle(range(steps - 1, -1, -1) + range(steps), 1000))
  values0f = Values(itertools.chain(xrange(steps), itertools.repeat(0, 1000)), steps)
  values0d = Values(itertools.chain(xrange(steps), itertools.repeat(steps - 1, 1000)), steps)
  values0b = Values(itertools.chain(xrange(steps - 1, -1, -1), itertools.repeat(steps - 1, 1000)), steps)
  values09 = Values(itertools.chain(xrange(steps - 1, -1, -1), itertools.repeat(0, 1000)), steps)

  def __init__(self, periodreg, shapereg):
    OscNode.__init__(self, periodreg)
    self.reset()
    self.shapeversion = None
    self.shapereg = shapereg

  def reset(self):
    self.progress = self.scaleofstep * 0xffff # Matching biggest possible stepsize.

  def callimpl(self):
    if self.shapeversion != self.shapereg.version:
      shape = self.shapereg.value & 0x0f
      if not (shape & 0x08):
        shape = (0x09, 0x0f)[bool(shape & 0x04)]
      self.values = getattr(self, "values%02x" % shape)
      self.shapeversion = self.shapereg.version
      self.valueindex = 0
      self.reset()
    self.stepsize = self.scaleofstep * self.periodreg.value
    # If progress beats the new stepsize, we terminate right away:
    cursor = min(self.block.framecount, max(0, self.stepsize - self.progress))
    cursor and self.blockbuf.fillpart(0, cursor, self.lastvalue)
    self.progress = min(self.progress + cursor, self.stepsize)
    if cursor == self.block.framecount:
      return
    fullsteps = (self.block.framecount - cursor) // self.stepsize
    if self.blockbuf.putringops(self.values.buf, self.valueindex, fullsteps) * self.stepsize < fullsteps:
      for i in xrange(self.stepsize):
        self.blockbuf.putring(cursor + i, self.stepsize, self.values.buf, self.valueindex, fullsteps)
      self.getvalue(fullsteps)
      cursor += fullsteps * self.stepsize
    else:
      for _ in xrange(fullsteps):
        self.blockbuf.fillpart(cursor, cursor + self.stepsize, self.getvalue())
        cursor += self.stepsize
    if cursor == self.block.framecount:
      return
    self.blockbuf.fillpart(cursor, self.block.framecount, self.getvalue())
    self.progress = self.block.framecount - cursor
