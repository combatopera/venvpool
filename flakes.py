#!/bin/bash

eval "notexpr=($(cat .flakesignore))"

find -name '*.py' -not '(' "${notexpr[@]}" ')' -exec pyflakes '{}' +
