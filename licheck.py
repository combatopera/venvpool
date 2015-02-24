#!/usr/bin/env python

import anchor, sys

def main():
    path = anchor.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    f = open(path)
    try:
        master = f.read()
    finally:
        f.close()
    for path in sys.argv[1:]:
        f = open(path)
        try:
            text = f.read()
        finally:
            f.close()
        if text.startswith('#!'):
            for _ in xrange(2):
                text = text[text.index('\n') + 1:]
        if master != text[:len(master)]:
            raise Exception(path)

if '__main__' == __name__:
    main()
