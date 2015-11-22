#!/bin/bash

while ! [[ -e .hg || -e .svn ]]; do cd ..; done

for tag in XXX TODO FIXME; do

  find '(' -name '*.py' -or -name '*.pyx' ')' -exec pcregrep --color=always "$tag LATER" '{}' +

  find '(' -name '*.py' -or -name '*.pyx' ')' -exec pcregrep --color=always "$tag(?! LATER)" '{}' +

done
