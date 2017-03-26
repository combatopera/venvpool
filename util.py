import sys, os

def stderr(obj):
    sys.stderr.write(str(obj))
    sys.stderr.write(os.linesep)
