#!/bin/sh
#
# Script to control Yabi in dev and test
#

TOPDIR=$(cd `dirname $0`; pwd)

# break on error
set -e

ACTION="$1"

DATE=`date +%Y.%m.%d`
: ${PROJECT_NAME:='angelman'}
VIRTUALENV="${TOPDIR}/virt_${PROJECT_NAME}"
AWS_STAGING_INSTANCE='ccg_syd_nginx_staging'

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
    echo " ./develop.sh (dev|dev_rebuild|dev_full|runtests|lettuce)"
    echo " ./develop.sh (baseimage|buildimage|devimage|releasetarball|releaseimage)"
    echo " ./develop.sh (start_release|start_release_rebuild)"
    echo " ./develop.sh (pythonlint|jslint)"
    echo " ./develop.sh (ci_docker_staging|docker_staging_lettuce|ci_rpm_staging|docker_rpm_staging_lettuce)"
    echo " ./develop.sh (ci_dockerbuild)"
    echo " ./develop.sh (rpmbuild|rpm_publish)"
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


_docker_options() {
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

    if [ -z ${bamboo_CI_SSH_KEY+x} ]; then
	info "loading default ssh keys"
        ssh-add || true
    else
	info "loading bamboo_CI_SSH_KEY ssh keys"
        ssh-add ${bamboo_CI_SSH_KEY} || true
    fi
}


# figure out what branch/tag we are on, write out .version file
_bb_revision() {
    info 'git revision'

    set +e
    gittag=`git describe --abbrev=0 --tags 2> /dev/null`
    set -e
    gitbranch=`git rev-parse --abbrev-ref HEAD 2> /dev/null`

    if [ $gitbranch = "HEAD" ]; then
        fail 'git clone is in detached HEAD state'
    fi

    # only use tags when on master (release) branch
    if [ $gitbranch != "master" ]; then
        info 'Ignoring tags, not on master branch'
        gittag=$gitbranch
    fi

    # if no git tag, then use branch name
    if [ -z ${gittag+x} ]; then
        info 'No git tag set, using branch name'
        gittag=$gitbranch
    fi

    # create .version file for invalidating cache in Dockerfile
    # we hit remote as the Dockerfile clones remote
    git ls-remote git@bitbucket.org:ccgmurdoch/${PROJECT_NAME}.git ${gittag} > .version

    success "$(cat .version)"
    success "git tag: ${gittag}"
}


create_dev_image() {
    info 'create dev image'
    set -x
    (${CMD_ENV}; docker build ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_PIP_PROXY} -t muccg/${PROJECT_NAME}-dev -f Dockerfile-dev .)
    set +x
}


create_release_image() {
    info 'create release image'
    # assumes that base image and release tarball have been created
    _docker_release_build Dockerfile-release ${DOCKER_IMAGE}
    success "$(docker images | grep ${DOCKER_IMAGE} | grep ${gittag}-${DATE} | sed 's/  */ /g')"
}


create_build_image() {
    info 'create build image'
    _bb_revision

    set -x
    # don't try and pull the build image
    (${CMD_ENV}; docker build ${DOCKER_BUILD_NOCACHE} ${DOCKER_BUILD_PROXY} --build-arg ARG_GIT_TAG=${gittag} -t muccg/${PROJECT_NAME}-build -f Dockerfile-build .)
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

    set -x
    local volume=$(readlink -f ./build/)
    (${CMD_ENV}; docker run ${DOCKER_RUN_OPTS} --rm -v ${volume}:/data muccg/${PROJECT_NAME}-build tarball)
    set +x
    success "$(ls -lh build/*)"
}


start_release() {
    info 'start release'
    mkdir -p data/release
    chmod o+rwx data/release

    set -x
    GIT_TAG=${gittag} docker-compose --project-name ${PROJECT_NAME} -f docker-compose-release.yml rm --force
    GIT_TAG=${gittag} docker-compose --project-name ${PROJECT_NAME} -f docker-compose-release.yml up
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


start_dev_full() {
    info 'start dev full'
    mkdir -p data/dev
    chmod o+rwx data/dev
    set -x
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} -f docker-compose-full.yml up)
    set +x
}


# build RPMs
rpm_build() {
    info 'rpm build'
    mkdir -p data/rpmbuild
    chmod o+rwx data/rpmbuild
    set -x
    docker-compose ${DOCKER_COMPOSE_OPTIONS} --project-name ${PROJECT_NAME} -f docker-compose-rpmbuild.yml pull
    (${CMD_ENV}; docker-compose ${DOCKER_COMPOSE_OPTIONS} --project-name ${PROJECT_NAME} -f docker-compose-rpmbuild.yml up)
    set +x
    success "$(ls -lht data/rpmbuild/RPMS/x86_64/rdrf* | head -1)"
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


_docker_release_build() {
    info 'docker release build'

    local dockerfile='Dockerfile-release'
    local dockerimage=${DOCKER_IMAGE}

    _bb_revision

    # attempt to warm up docker cache
    if [ ${DOCKER_USE_HUB} = "1" ]; then
        docker pull ${dockerimage}:${gittag} || true
    fi

    for tag in "${dockerimage}:${gittag}" "${dockerimage}:${gittag}-${DATE}"; do
        info "Building ${PROJECT_NAME} ${tag}"
        set -x
	# don't try and pull the base image
	(${CMD_ENV}; docker build ${DOCKER_BUILD_PROXY} ${DOCKER_BUILD_NOCACHE} --build-arg ARG_GIT_TAG=${gittag} -t ${tag} -f ${dockerfile} .)
        set +x
	success "built ${tag}"

        if [ ${DOCKER_USE_HUB} = "1" ]; then
            set -x
            docker push ${tag}
            set +x
	    success "pushed ${tag}"
        fi
    done

    rm -f .version || true
    success 'docker release build'
}


# docker build and push in CI
ci_dockerbuild() {
    info 'ci docker build'
    _ci_docker_login
    create_base_image
    create_build_image
    create_release_tarball
    _docker_release_build
    success 'ci docker build'
}


_test_stack_up() {
    info 'test stack up'
    mkdir -p data/tests
    chmod o+rwx data/tests

    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml rm --force
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml up -d
    set +x
    success 'test stack up'
}


_test_stack_down() {
    info 'test stack down'
    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml stop
    set +x
    success 'test stack down'
}


run_unit_tests() {
    info 'run unit tests'
    _test_stack_up

    set +e
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-unittests.yml rm --force
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-unittests.yml up
    rval=$?
    set -e

    _test_stack_down

    return $rval
}


# publish rpms to testing repo
rpm_publish() {
    info 'rpm publish'
    pip install pyyaml
    time ccg publish_testing_rpm:data/rpmbuild/RPMS/x86_64/rdrf*.rpm,release=6
    success 'rpm publish'
}


# build a docker image and start stack on staging using docker-compose
ci_docker_staging() {
    info 'ci docker staging'
    ssh ubuntu@staging.ccgapps.com.au << EOF
      mkdir -p ${PROJECT_NAME}/data
      chmod o+w ${PROJECT_NAME}/data
EOF

    scp docker-compose-*.yml ubuntu@staging.ccgapps.com.au:${PROJECT_NAME}/

    # TODO This doesn't actually do a whole lot, some tests should be run against the staging stack
    ssh ubuntu@staging.ccgapps.com.au << EOF
      cd ${PROJECT_NAME}
      docker-compose -f docker-compose-staging.yml stop
      docker-compose -f docker-compose-staging.yml kill
      docker-compose -f docker-compose-staging.yml rm --force -v
      docker-compose -f docker-compose-staging.yml up -d
EOF
}


_selenium_stack_up() {
    info 'selenium stack up'
    mkdir -p data/selenium
    chmod o+rwx data/selenium

    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-selenium.yml up -d
    set +x
    success 'selenium stack up'
}


_selenium_stack_down() {
    info 'selenium stack down'
    set -x
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-selenium.yml stop
    set +x
    success 'selenium stack down'
}


lettuce() {
    info 'lettuce'
    _selenium_stack_up
    _test_stack_up

    set -x
    set +e
    ( docker-compose --project-name ${PROJECT_NAME} -f docker-compose-lettuce.yml rm --force || exit 0 )
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} -f docker-compose-lettuce.yml build)
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-lettuce.yml up
    rval=$?
    set -e
    set +x

    _test_stack_down
    _selenium_stack_down

    exit $rval
}


docker_staging_lettuce() {
    _selenium_stack_up

    set -x
    set +e
    ( docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml rm --force || exit 0 )
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml build)
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml up
    rval=$?
    set -e
    set +x

    _selenium_stack_down

    exit $rval
}


docker_rpm_staging_lettuce() {
    _selenium_stack_up

    set -x
    set +e
    ( docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-rpm-lettuce.yml rm --force || exit 0 )
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-rpm-lettuce.yml build)
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-rpm-lettuce.yml up
    rval=$?
    set -e
    set +x

    _selenium_stack_down

    exit $rval
}


# lint using flake8
python_lint() {
    info "python lint"
    pip install 'flake8>=2.0,<2.1'
    flake8 rdrf --exclude=migrations,selenium_test --ignore=E501 --count
    success "python lint"
}


# lint js, assumes closure compiler
js_lint() {
    info "js lint"
    pip install 'closure-linter==2.3.13'
    JSFILES=`ls rdrf/rdrf/static/js/*.js | grep -v "\.min\."`
    EXCLUDES='-x rdrf/rdrf/static/js/gallery.js,rdrf/rdrf/static/js/ie_select.js,rdrf/rdrf/static/js/jquery.bootgrid.js,rdrf/rdrf/static/js/nv.d3.js'
    for JS in $JSFILES
    do
        gjslint ${EXCLUDES} --disable 0131 --max_line_length 100 --nojsdoc $JS
    done
    success "js lint"
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


echo ''
info "$0 $@"
make_virtualenv

_docker_options

case $ACTION in
pythonlint)
    python_lint
    ;;
jslint)
    js_lint
    ;;
dev)
    start_dev
    ;;
dev_rebuild)
    create_base_image
    create_build_image
    create_dev_image
    start_dev
    ;;
dev_full)
    start_dev_full
    ;;
releasetarball)
    create_release_tarball
    ;;
start_release)
    start_release
    ;;
start_release_rebuild)
    create_base_image
    create_build_image
    create_release_tarball
    create_release_image
    start_release
    ;;
rpmbuild)
    rpm_build
    ;;
baseimage)
    create_base_image
    ;;
buildimage)
    create_build_image
    ;;
releaseimage)
    create_release_image
    ;;
devimage)
    create_dev_image
    ;;
ci_dockerbuild)
    ci_dockerbuild
    ;;
rpm_publish)
    _ci_ssh_agent
    rpm_publish
    ;;
runtests)
    create_base_image
    create_build_image
    create_dev_image
    run_unit_tests
    ;;
ci_docker_staging)
    _ci_ssh_agent
    ci_docker_staging
    ;;
ci_rpm_staging)
    _ci_ssh_agent
    ci_rpm_staging
    ;;
docker_staging_lettuce)
    docker_staging_lettuce
    ;;
docker_rpm_staging_lettuce)
    docker_rpm_staging_lettuce
    ;;
lettuce)
    create_base_image
    create_build_image
    create_dev_image
    lettuce
    ;;
*)
    usage
    ;;
esac
