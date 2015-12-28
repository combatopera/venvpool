#!/usr/bin/env runpy

import subprocess, sys, os

def findfiles(*suffixes):
    for dirpath, dirnames, filenames in os.walk('.'):
        for name in sorted(filenames):
            for suffix in suffixes:
                if name.endswith(suffix):
                    break
            else:
                continue
            yield os.path.join(dirpath, name)
        dirnames.sort()

bashscript = '''set -e

while ! [[ -e .hg || -e .svn ]]; do cd ..; done

(

    IFS=$'\n'

    for script in licheck nlcheck; do
        $script.py $(
            find '(' -name '*.py' -or -name '*.pyx' -or -name '*.s' -or -name '*.sh' ')' -exec hg st -A '{}' + |
            grep -v '^[IR ]' |
            cut -c 3-
        )
        echo $script: OK >&2
    done

    divcheck.py $(find -name '*.py')
    echo divcheck: OK >&2

    execcheck.py $(find -name '*.py')
    echo execcheck: OK >&2

)

eval "notexpr=($(cat .flakesignore))"

{ find -name '*.py' -not '(' "${notexpr[@]}" ')' -exec pyflakes '{}' + && echo pyflakes: OK; } >&2
'''

def main():
    subprocess.check_call(['bash', '-c', bashscript])
    sys.exit(subprocess.call(['nosetests', '--exe', '-v']))

if '__main__' == __name__:
    main()
