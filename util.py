import sys, os

def stderr(text):
    sys.stderr.write(text)
    sys.stderr.write(os.linesep)
