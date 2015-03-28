#!/usr/bin/env python

import sys, re, ast

def main():
    for path in sys.argv[1:]:
        f = open(path)
        try:
            text = f.read()
        finally:
            f.close()
        for node in ast.walk(ast.parse(text)):
            if 'Div' == type(node).__name__:
                hasdiv = True
                break
        else:
            hasdiv = False
        if hasdiv == (re.search('^from __future__ import division$', text, flags = re.MULTILINE) is None):
            raise Exception(path)

if '__main__' == __name__:
    main()
