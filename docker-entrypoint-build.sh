#!/bin/bash

info () {
    printf "\r  [\033[00;34mINFO\033[0m] %s\n" "$1"
}

trap exit SIGHUP SIGINT SIGTERM
env | grep -iv PASS | sort

if [ "$1" = 'checkout' ]; then
    info "[Run] checkout"
    info "[Run] Clone the source code"
    info "BUILD_VERSION ${BUILD_VERSION}"
    info "PROJECT_SOURCE ${PROJECT_SOURCE}"

    set -e
    rm -rf "/data/app/"
    mkdir "/data/app/"

    # clone and install the app
    set -x
    cd /data/app
    git clone --depth=1 --branch="${GIT_BRANCH}" "${PROJECT_SOURCE}" .
    git rev-parse HEAD > .version
    cat .version
    exit 0
fi


# prepare a tarball of build
if [ "$1" = 'releasetarball' ]; then
    info "[Run] Preparing a release tarball"
    info "BUILD_VERSION ${BUILD_VERSION}"
    info "PROJECT_SOURCE ${PROJECT_SOURCE}"
	cd /data/app
	
    pip install --upgrade "setuptools>=36.0.0,<=37.0.0"
	
    #pip install -e "${PROJECT_NAME}"
    cd "${PROJECT_NAME}" && pip install .

    set +x
	
	cd /data
    rm -rf env
    cp -rp /env .
    # vars for creating release tarball
    ARTIFACTS="env
               app/docker-entrypoint.sh
               app/uwsgi
               app/scripts
               app/${PROJECT_NAME}"
    TARBALL="/data/${PROJECT_NAME}-${BUILD_VERSION}.tar"
    # shellcheck disable=SC2037
    TAR_OPTS="--exclude-vcs
              --exclude=app/rdrf/rdrf/frontend/*
              --verify
              --checkpoint=1000
              --checkpoint-action=dot
              --create
              --preserve-permissions"

    info "ARTIFACTS ${ARTIFACTS}"
    info "TARBALL ${TARBALL}"

    # create tar from / so relative and absolute paths are identical
    # allows archive verification to work
    
    set -x
    # shellcheck disable=SC2086
    rm -f "${TARBALL}" && tar ${TAR_OPTS} -f "${TARBALL}" ${ARTIFACTS}
    set +x
    info "$(ls -lath "${TARBALL}")"
    rm -f "${TARBALL}.gz" && gzip "${TARBALL}"
    info "$(ls -lath "${TARBALL}.gz")"
    exit 0
fi

info "[RUN]: Builtin command not provided [checkout|releasetarball]"
info "[RUN]: $*"

exec "$@"
