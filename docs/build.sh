#!/bin/sh

TOPDIR=$(cd `dirname $0`; pwd)
DATE=`date +%Y.%m.%d`
VIRTUALENV="${TOPDIR}/virt"

info () {
  printf "\r  [ \033[00;34mINFO\033[0m ] $1\n"
}

success () {
  printf "\r\033[2K  [ \033[00;32m OK \033[0m ] $1\n"
}


fail () {
  printf "\r\033[2K  [\033[0;31mFAIL\033[0m] $1\n"
  echo ''
  exit 1
}


make_virtualenv() {
    info "make virtualenv"
    # check requirements
    if ! which virtualenv > /dev/null; then
      fail "virtualenv is required by develop.sh but it isn't installed."
    fi
    if [ ! -e ${VIRTUALENV} ]; then
        virtualenv ${VIRTUALENV}
    fi
    . ${VIRTUALENV}/bin/activate

    if ! which sphinx-build > /dev/null; then
      pip install 'Sphinx' --upgrade || true
      pip install sphinx_rtd_theme -- upgrade || true
    fi
    success "$(shpinx-build --version)"
}


build() {
    make_virtualenv
    make html
}

build
