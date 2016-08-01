#!/bin/sh
#
# common definitons shared between projects
#
set -a

TOPDIR=$(cd `dirname $0`; pwd)
DATE=`date +%Y.%m.%d`

: ${DOCKER_BUILD_PROXY:="--build-arg http_proxy"}
: ${DOCKER_USE_HUB:="0"}
: ${DOCKER_IMAGE:="muccg/${PROJECT_NAME}"}
: ${SET_HTTP_PROXY:="1"}
: ${SET_PIP_PROXY:="1"}
: ${DOCKER_NO_CACHE:="0"}
: ${DOCKER_PULL:="1"}

# Do not set these, they are vars used below
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
    echo " ./develop.sh (ci_docker_staging|docker_staging_lettuce)"
    echo " ./develop.sh (ci_docker_login)"
    echo ""
    echo "Example, start dev with no proxy and rebuild everything:"
    echo "SET_PIP_PROXY=0 SET_HTTP_PROXY=0 ./develop.sh dev_build"
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
}


_http_proxy() {
    info 'http proxy'

    if [ ${SET_HTTP_PROXY} = "1" ]; then
        if [ -z ${HTTP_PROXY_HOST+x} ]; then
            HTTP_PROXY_HOST=${DOCKER_ROUTE}
        fi
        http_proxy="http://${HTTP_PROXY_HOST}:3128"
        HTTP_PROXY="http://${HTTP_PROXY_HOST}:3128"
        NO_PROXY=${HTTP_PROXY_HOST}
        no_proxy=${HTTP_PROXY_HOST}
        success "Proxy $http_proxy"
    else
        info 'Not setting http_proxy'
    fi

    export HTTP_PROXY http_proxy NO_PROXY no_proxy

    success "HTTP proxy ${HTTP_PROXY}"
}


_pip_proxy() {
    info 'pip proxy'

    # pip defaults
    PIP_INDEX_URL='https://pypi.python.org/simple'
    PIP_TRUSTED_HOST='127.0.0.1'

    if [ ${SET_PIP_PROXY} = "1" ]; then
        if [ -z ${PIP_PROXY_HOST+x} ]; then
            PIP_PROXY_HOST=${DOCKER_ROUTE}
        fi
        # use a local devpi install
        PIP_INDEX_URL="http://${PIP_PROXY_HOST}:3141/root/pypi/+simple/"
        PIP_TRUSTED_HOST="${PIP_PROXY_HOST}"
    fi

    export PIP_INDEX_URL PIP_TRUSTED_HOST

    success "Pip index url ${PIP_INDEX_URL}"
}


docker_warm_cache() {
    # attempt to warm up docker cache by pulling next_release tag
    if [ ${DOCKER_USE_HUB} = "1" ]; then
        info 'warming docker cache'
        set -x
        docker pull ${DOCKER_IMAGE}:next_release || true
        set +x
    fi
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


ci_docker_login() {
    info 'Docker login'

    if [ -z ${DOCKER_USERNAME+x} ]; then
        DOCKER_USERNAME=${bamboo_DOCKER_USERNAME}
    fi
    if [ -z ${DOCKER_PASSWORD+x} ]; then
        DOCKER_PASSWORD=${bamboo_DOCKER_PASSWORD}
    fi

    if [ -z ${DOCKER_USERNAME} ] || [ -z ${DOCKER_PASSWORD} ]; then
        fail "Docker credentials not available"
    fi

    docker login -u ${DOCKER_USERNAME} --password="${DOCKER_PASSWORD}"
    success "Docker login"
}


# figure out what branch/tag we are on
git_tag() {
    info 'git tag'

    set +e
    GIT_TAG=`git describe --abbrev=0 --tags 2> /dev/null`
    set -e

    # jenksins sets BRANCH_NAME, so we use that
    # otherwise ask git
    GIT_BRANCH="${BRANCH_NAME}"
    if [ -z ${GIT_BRANCH} ]; then
        GIT_BRANCH=`git rev-parse --abbrev-ref HEAD 2> /dev/null`
    fi

    # fail when we don't know branch
    if [ "${GIT_BRANCH}" = "HEAD" ]; then
        fail 'git clone is in detached HEAD state and BRANCH_NAME not set'
    fi

    # only use tags when on master (prod) branch
    if [ "${GIT_BRANCH}" != "master" ]; then
        info 'Ignoring tags, not on master branch'
        GIT_TAG=${GIT_BRANCH}
    fi

    # if no git tag, then use branch name
    if [ -z ${GIT_TAG+x} ]; then
        info 'No git tag set, using branch name'
        GIT_TAG=${GIT_BRANCH}
    fi

    export GIT_TAG

    success "git tag: ${GIT_TAG}"
}


create_dev_image() {
    info 'create dev image'
    set -x
    docker-compose -f docker-compose-build.yml build ${DOCKER_COMPOSE_BUILD_NOCACHE} dev
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-dev | sed 's/  */ /g')"
}


create_build_image() {
    info 'create build image'
    set -x
    docker-compose -f docker-compose-build.yml build ${DOCKER_COMPOSE_BUILD_NOCACHE} build
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-build | sed 's/  */ /g')"
}


create_base_image() {
    info 'create base image'
    set -x
    docker-compose -f docker-compose-build.yml build ${DOCKER_COMPOSE_BUILD_OPTS} base
    set +x
    success "$(docker images | grep muccg/${PROJECT_NAME}-base | sed 's/  */ /g')"
}


create_prod_image() {
    info 'create prod image'
    info "Building ${PROJECT_NAME} ${GIT_TAG}"
    set -x
    docker-compose -f docker-compose-build.yml build prod
    set +x
    success "$(docker images | grep ${DOCKER_IMAGE} | grep ${GIT_TAG} | sed 's/  */ /g')"
    docker tag ${DOCKER_IMAGE}:${GIT_TAG} ${DOCKER_IMAGE}:${GIT_TAG}-${DATE}
    success 'create prod image'
}


create_release_tarball() {
    info 'create release tarball'
    mkdir -p build
    chmod o+rwx build
    set -x
    docker-compose -f docker-compose-build.yml run build
    set +x
    success "$(ls -lh build/* | grep ${GIT_TAG})"
}


start_prod() {
    info 'start prod'
    mkdir -p data/prod
    chmod o+rwx data/prod

    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-prod.yml rm --force
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-prod.yml up
    set +x
}


start_dev() {
    info 'start dev'
    mkdir -p data/dev
    chmod o+rwx data/dev

    set -x
    docker-compose --project-name ${PROJECT_NAME} up
    set +x
}


publish_docker_image() {
    # check we are on master or next_release
    if [ "${GIT_BRANCH}" = "master" ] || [ "${GIT_BRANCH}" = "next_release" ]; then
        info "publishing docker image for ${GIT_BRANCH} branch, version ${GIT_TAG}"
    else
        info "skipping publishing docker image for ${GIT_BRANCH} branch"
        return
    fi

    if [ ${DOCKER_USE_HUB} = "1" ]; then
        docker push ${DOCKER_IMAGE}:${GIT_TAG}
        docker push ${DOCKER_IMAGE}:${GIT_TAG}-${DATE}
        success "pushed ${tag}"
    else
        info "docker push of ${GIT_TAG} disabled by config"
    fi
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
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-unittests.yml run --rm testhost
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
