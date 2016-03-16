#!/bin/sh
#
# common definitons shared between projects
#

TOPDIR=$(cd `dirname $0`; pwd)
DATE=`date +%Y.%m.%d`
VIRTUALENV="${TOPDIR}/virt_${PROJECT_NAME}"

: ${DOCKER_BUILD_PROXY:="--build-arg http_proxy"}
: ${DOCKER_USE_HUB:="0"}
: ${DOCKER_IMAGE:="muccg/${PROJECT_NAME}"}
: ${SET_HTTP_PROXY:="1"}
: ${SET_PIP_PROXY:="1"}
: ${DOCKER_NO_CACHE:="0"}
: ${DOCKER_PULL:="1"}

# Do not set these, they are vars used below
CMD_ENV=''
DOCKER_ROUTE=''
DOCKER_BUILD_OPTS=''
DOCKER_RUN_OPTS='-e PIP_INDEX_URL -e PIP_TRUSTED_HOST'
DOCKER_COMPOSE_BUILD_OPTS=''


usage() {
    echo ""
    echo "Environment:"
    echo " Pull during build              DOCKER_PULL                 ${DOCKER_PULL} "
    echo " No cache during build          DOCKER_NO_CACHE             ${DOCKER_NO_CACHE} "
    echo " Use proxy during builds        DOCKER_BUILD_PROXY          ${DOCKER_BUILD_PROXY}"
    echo " Push/pull from docker hub      DOCKER_USE_HUB              ${DOCKER_USE_HUB}"
    echo " Release docker image           DOCKER_IMAGE                ${DOCKER_IMAGE}"
    echo " Use a http proxy               SET_HTTP_PROXY              ${SET_HTTP_PROXY}"
    echo " Use a pip proxy                SET_PIP_PROXY               ${SET_PIP_PROXY}"
    echo ""
    echo "Usage:"
    echo " ./develop.sh (baseimage|buildimage|devimage|releasetarball|prodimage)"
    echo " ./develop.sh (dev|dev_build)"
    echo " ./develop.sh (start_prod|prod_build)"
    echo " ./develop.sh (runtests|lettuce|selenium)"
    echo " ./develop.sh (start_test_stack|start_seleniumhub|start_seleniumtests|start_prodseleniumtests)"
    echo " ./develop.sh (pythonlint|jslint)"
    echo " ./develop.sh (ci_dockerbuild)"
    echo " ./develop.sh (ci_docker_staging|docker_staging_lettuce)"
    echo ""
    echo "Example, start dev with no proxy and rebuild everything:"
    echo "SET_PIP_PROXY=0 SET_HTTP_PROXY=0 ./develop.sh dev_rebuild"
    echo ""
    exit 1
}


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


docker_options() {
    DOCKER_ROUTE=$(ip -4 addr show docker0 | grep -Po 'inet \K[\d.]+')
    success "Docker ip ${DOCKER_ROUTE}"

    _http_proxy
    _pip_proxy

    if [ ${DOCKER_PULL} = "1" ]; then
         DOCKER_BUILD_PULL="--pull=true"
         DOCKER_COMPOSE_BUILD_PULL="--pull"
    else
         DOCKER_BUILD_PULL="--pull=false"
         DOCKER_COMPOSE_BUILD_PULL=""
    fi

    if [ ${DOCKER_NO_CACHE} = "1" ]; then
         DOCKER_BUILD_NOCACHE="--no-cache=true"
         DOCKER_COMPOSE_BUILD_NOCACHE="--no-cache"
    else
         DOCKER_BUILD_NOCACHE="--no-cache=false"
         DOCKER_COMPOSE_BUILD_NOCACHE=""
    fi

    DOCKER_BUILD_OPTS="${DOCKER_BUILD_OPTS} ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_PULL} ${DOCKER_BUILD_PIP_PROXY}"

    # compose does not expose all docker functionality, so we can't use compose to build in all cases
    DOCKER_COMPOSE_BUILD_OPTS="${DOCKER_COMPOSE_BUILD_OPTS} ${DOCKER_COMPOSE_BUILD_NOCACHE} ${DOCKER_COMPOSE_BUILD_PULL}"

    # environemnt used by subshells
    CMD_ENV="export ${CMD_ENV}"
}


_http_proxy() {
    info 'http proxy'

    if [ ${SET_HTTP_PROXY} = "1" ]; then
        local http_proxy="http://${DOCKER_ROUTE}:3128"
	CMD_ENV="${CMD_ENV} http_proxy=http://${DOCKER_ROUTE}:3128"
        success "Proxy $http_proxy"
    else
        info 'Not setting http_proxy'
    fi
}


_pip_proxy() {
    info 'pip proxy'

    # pip defaults
    PIP_INDEX_URL='https://pypi.python.org/simple'
    PIP_TRUSTED_HOST='127.0.0.1'

    if [ ${SET_PIP_PROXY} = "1" ]; then
        # use a local devpi install
	PIP_INDEX_URL="http://${DOCKER_ROUTE}:3141/root/pypi/+simple/"
	PIP_TRUSTED_HOST="${DOCKER_ROUTE}"
    fi

    CMD_ENV="${CMD_ENV} NO_PROXY=${DOCKER_ROUTE} no_proxy=${DOCKER_ROUTE} PIP_INDEX_URL=${PIP_INDEX_URL} PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}"
    DOCKER_BUILD_PIP_PROXY='--build-arg ARG_PIP_INDEX_URL='${PIP_INDEX_URL}' --build-arg ARG_PIP_TRUSTED_HOST='${PIP_TRUSTED_HOST}''

    success "Pip index url ${PIP_INDEX_URL}"
}


# ssh setup for ci
_ci_ssh_agent() {
    info 'ci ssh config'

    ssh-agent > /tmp/agent.env.sh
    . /tmp/agent.env.sh
    success "started ssh-agent"

    # load key if defined by bamboo
    if [ -z ${bamboo_CI_SSH_KEY+x} ]; then
	info "loading default ssh keys"
        ssh-add || true
    else
	info "loading bamboo_CI_SSH_KEY ssh keys"
        ssh-add ${bamboo_CI_SSH_KEY} || true
    fi

    # some private projects had a deployment key
    if [ -f docker-build.key ]; then
        chmod 600 docker-build.key
        ssh-add docker-build.key
    fi

    ssh-add -l
}


_ci_docker_login() {
    info 'Docker login'

    if [ -z ${bamboo_DOCKER_EMAIL+x} ]; then
        fail 'bamboo_DOCKER_EMAIL not set'
    fi
    if [ -z ${bamboo_DOCKER_USERNAME+x} ]; then
        fail 'bamboo_DOCKER_USERNAME not set'
    fi
    if [ -z ${bamboo_DOCKER_PASSWORD+x} ]; then
        fail 'bamboo_DOCKER_PASSWORD not set'
    fi

    docker login  -e "${bamboo_DOCKER_EMAIL}" -u ${bamboo_DOCKER_USERNAME} --password="${bamboo_DOCKER_PASSWORD}"
    success "Docker login"
}


# figure out what branch/tag we are on
_git_tag() {
    info 'git tag'

    set +e
    gittag=`git describe --abbrev=0 --tags 2> /dev/null`
    set -e
    gitbranch=`git rev-parse --abbrev-ref HEAD 2> /dev/null`

    # fail error for an error condition we see on bamboo occasionaly
    if [ $gitbranch = "HEAD" ]; then
        fail 'git clone is in detached HEAD state'
    fi

    # only use tags when on master (prod) branch
    if [ $gitbranch != "master" ]; then
        info 'Ignoring tags, not on master branch'
        gittag=$gitbranch
    fi

    # if no git tag, then use branch name
    if [ -z ${gittag+x} ]; then
        info 'No git tag set, using branch name'
        gittag=$gitbranch
    fi

    success "git tag: ${gittag}"
}


create_dev_image() {
    info 'create dev image'
    set -x
    (${CMD_ENV}; docker build ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_PIP_PROXY} -t muccg/${PROJECT_NAME}-dev -f Dockerfile-dev .)
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-dev | sed 's/  */ /g')"
}


create_build_image() {
    info 'create build image'

    set -x
    # don't try and pull the build image
    (${CMD_ENV}; docker build ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} -t muccg/${PROJECT_NAME}-build -f Dockerfile-build .)
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-build | sed 's/  */ /g')"
}


create_base_image() {
    info 'create base image'
    set -x
    (${CMD_ENV}; docker build ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_PULL} -t muccg/${PROJECT_NAME}-base -f Dockerfile-base .)
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-base | sed 's/  */ /g')"
}


create_release_tarball() {
    info 'create release tarball'
    mkdir -p build
    chmod o+rwx build

    _git_tag

    set -x
    local volume=$(readlink -f ./build/)
    (${CMD_ENV}; docker run -e GIT_TAG=${gittag} ${DOCKER_RUN_OPTS} --rm -v ${volume}:/data muccg/${PROJECT_NAME}-build tarball)
    set +x
    success "$(ls -lh build/* | grep ${gittag})"
}


start_prod() {
    info 'start prod'
    mkdir -p data/prod
    chmod o+rwx data/prod

    _git_tag

    set -x
    GIT_TAG=${gittag} docker-compose --project-name ${PROJECT_NAME} -f docker-compose-prod.yml rm --force
    GIT_TAG=${gittag} docker-compose --project-name ${PROJECT_NAME} -f docker-compose-prod.yml up
    set +x
}


start_dev() {
    info 'start dev'
    mkdir -p data/dev
    chmod o+rwx data/dev

    set -x
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} up)
    set +x
}


create_prod_image() {
    info 'create prod image'

    _git_tag

    # attempt to warm up docker cache
    if [ ${DOCKER_USE_HUB} = "1" ]; then
        docker pull ${DOCKER_IMAGE}:${gittag} || true
    fi

    for tag in "${DOCKER_IMAGE}:${gittag}" "${DOCKER_IMAGE}:${gittag}-${DATE}"; do
        info "Building ${PROJECT_NAME} ${tag}"
        set -x
	# don't try and pull the base image
	(${CMD_ENV}; docker build ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_NOCACHE} --build-arg ARG_GIT_TAG=${gittag} -t ${tag} -f Dockerfile-prod .)
        set +x
        success "$(docker images | grep ${DOCKER_IMAGE} | grep ${gittag} | sed 's/  */ /g')"

        if [ ${DOCKER_USE_HUB} = "1" ]; then
            set -x
            docker push ${tag}
            set +x
	    success "pushed ${tag}"
        fi
    done

    success 'create prod image'
}


_start_test_stack() {
    info 'test stack up'
    mkdir -p data/tests
    chmod o+rwx data/tests

    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml up $@
    set +x
    success 'test stack up'
}


_stop_test_stack() {
    info 'test stack down'
    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml stop
    set +x
    success 'test stack down'
}


start_test_stack() {
    _start_test_stack --force-recreate
}


run_unit_tests() {
    info 'run unit tests'
    _start_test_stack --force-recreate -d

    set +e
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-unittests.yml up --force-recreate
    rval=$?
    set -e

    _stop_test_stack

    return $rval
}


_start_selenium() {
    info 'selenium stack up'
    mkdir -p data/selenium
    chmod o+rwx data/selenium

    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-selenium.yml up $@
    set +x
    success 'selenium stack up'
}


_stop_selenium() {
    info 'selenium stack down'
    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-selenium.yml stop
    set +x
    success 'selenium stack down'
}


start_seleniumhub() {
    _start_selenium --force-recreate
}


start_lettucetests() {
    set -x
    set +e
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-lettuce.yml up --force-recreate
    local rval=$?
    set -e
    set +x

    return $rval
}


lettuce() {
    info 'lettuce'
    _start_selenium --force-recreate -d
    _start_test_stack --force-recreate -d

    start_lettucetests
    local rval=$?

    _stop_test_stack
    _stop_selenium

    exit $rval
}


start_seleniumtests() {
    set -x
    set +e
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-seleniumtests.yml up --force-recreate
    local rval=$?
    set -e
    set +x

    return $rval
}


selenium() {
    info 'selenium'
    _start_selenium --force-recreate -d
    _start_test_stack --force-recreate -d

    start_seleniumtests
    local rval=$?

    _stop_test_stack
    _stop_selenium

    exit $rval
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

    if ! which docker-compose > /dev/null; then
      pip install 'docker-compose<1.6' --upgrade || true
    fi
    success "$(docker-compose --version)"
}
