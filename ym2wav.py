#!/usr/bin/env python

import logging
from pym2149.out import WavWriter
from pym2149.util import initlogging
from pym2149.ymformat import ymopen
from pym2149.mix import Mixer
from cli import Config

log = logging.getLogger(__name__)

def main():
  initlogging()
  config = Config()
  inpath, outpath = config.args
  f = ymopen(inpath)
  try:
    for info in f.info:
      log.info(info)
    chip, session = config.createchipandsession(f.clock)
    stream = WavWriter(session.clock, Mixer(*chip.dacs), outpath)
    try:
      for frame in f:
        chip.update(frame)
        for b in session.blocks(f.framefreq):
          stream(b)
      stream.flush()
    finally:
      stream.close()
  finally:
    f.close()

if '__main__' == __name__:
  main()
