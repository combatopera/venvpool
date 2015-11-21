#!/bin/bash

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
