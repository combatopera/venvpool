#!/bin/bash

# Copyright 2014 Andrzej Cichocki

# This file is part of runpy.
#
# runpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# runpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with runpy.  If not, see <http://www.gnu.org/licenses/>.

set -e

confname=runpy.conf

context="$(dirname "$PWD/$1")"

while true; do

    confpath="$context/$confname"

    [[ -e "$confpath" ]] && break

    [[ / = "$context" ]] && {
        echo Not found: "$confname" >&2
        exit 1
    }

    context="$(dirname "$context")"

done

WORKSPACE="$(dirname "$(dirname "$0")")"

. "$confpath"

exec python "$@"
