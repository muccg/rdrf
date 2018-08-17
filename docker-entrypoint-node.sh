#!/bin/bash

info () {
    printf "\r  [\033[00;34mINFO\033[0m] %s\n" "$1"
}

trap exit SIGHUP SIGINT SIGTERM
env | grep -iv PASS | sort

if [ "$1" = 'build' ]; then
    info "[Run] Building frontend JS bundle"
    info "BUILD_VERSION ${BUILD_VERSION}"
    info "PROJECT_SOURCE ${PROJECT_SOURCE}"

    set -x
    yarn install --frozen-lockfile
    npm run build

    exit 0
fi

if [ "$1" = 'watch' ]; then
    info "[Run] Watch source and recompile on change"

    yarn install
    npm run watch

    exit 0
fi

info "[RUN]: Builtin command not provided [build|watch]"
info "[RUN]: $*"

exec "$@"
