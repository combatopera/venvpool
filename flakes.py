#!/bin/bash

find -name '*.py' -not '(' $(cat .flakesignore) ')' -exec pyflakes '{}' +
