#!/bin/sh
#
TOPDIR=$(cd `dirname $0`; pwd)


# break on error
set -e 

ACTION="$1"

DATE=`date +%Y.%m.%d`
PROJECT_NAME='rdrf'
VIRTUALENV="${TOPDIR}/virt_${PROJECT_NAME}"
AWS_STAGING_INSTANCE='ccg_syd_nginx_staging'

: ${DOCKER_BUILD_OPTIONS:="--pull=true"}


usage() {
    echo 'Usage ./develop.sh (pythonlint|jslint|start|dockerbuild|rpmbuild|rpm_publish|unit_tests|selenium|lettuce|ci_staging|registry_specific_tests)'
}


# ssh setup, make sure our ccg commands can run in an automated environment
ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    . /tmp/agent.env.sh
    ssh-add ~/.ssh/ccg-syd-staging-2014.pem
}


# docker build and push in CI
dockerbuild() {
    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    image="muccg/${PROJECT_NAME}"
    gittag=`git describe --abbrev=0 --tags 2> /dev/null`
    gitbranch=`git rev-parse --abbrev-ref HEAD 2> /dev/null`

    # only use tags when on master (release) branch
    if [ $gitbranch != "master" ]; then
        echo "Ignoring tags, not on master branch"
        gittag=$gitbranch
    fi

    # if no git tag, then use branch name
    if [ -z ${gittag+x} ]; then
        echo "No git tag set, using branch name"
        gittag=$gitbranch
    fi

    echo "############################################################# ${PROJECT_NAME} ${gittag}"

    # attempt to warm up docker cache
    docker pull ${image} || true

    for tag in "${image}:${gittag}" "${image}:${gittag}-${DATE}"; do
        echo "############################################################# ${PROJECT_NAME} ${tag}"
        set -x
        docker build ${DOCKER_BUILD_OPTIONS} --build-arg GIT_TAG=${gittag} -t ${tag} -f Dockerfile-release .
        docker push ${tag}
        set +x
    done
}


rpmbuild() {
    mkdir -p data/rpmbuild
    chmod o+rwx data/rpmbuild

    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    docker-compose --project-name rdrf -f fig-rpmbuild.yml up
}


rpm_publish() {
    time ccg publish_testing_rpm:data/rpmbuild/RPMS/x86_64/rdrf*.rpm,release=6
}


ci_staging() {
    ccg ${AWS_STAGING_INSTANCE} drun:'mkdir -p rdrf/docker/unstable'
    ccg ${AWS_STAGING_INSTANCE} drun:'mkdir -p rdrf/data'
    ccg ${AWS_STAGING_INSTANCE} drun:'chmod o+w rdrf/data'
    ccg ${AWS_STAGING_INSTANCE} putfile:fig-staging.yml,rdrf/fig-staging.yml
    ccg ${AWS_STAGING_INSTANCE} putfile:docker/unstable/Dockerfile,rdrf/docker/unstable/Dockerfile

    ccg ${AWS_STAGING_INSTANCE} drun:'cd rdrf && fig -f fig-staging.yml stop'
    ccg ${AWS_STAGING_INSTANCE} drun:'cd rdrf && fig -f fig-staging.yml kill'
    ccg ${AWS_STAGING_INSTANCE} drun:'cd rdrf && fig -f fig-staging.yml rm --force -v'
    ccg ${AWS_STAGING_INSTANCE} drun:'cd rdrf && fig -f fig-staging.yml build --no-cache webstaging'
    ccg ${AWS_STAGING_INSTANCE} drun:'cd rdrf && fig -f fig-staging.yml up -d'
    ccg ${AWS_STAGING_INSTANCE} drun:'docker-clean || true'
}

lettuce() {
    mkdir -p data/selenium
    chmod o+rwx data/selenium

    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    docker-compose --project-name rdrf -f fig-lettuce.yml rm --force
    docker-compose --project-name rdrf -f fig-lettuce.yml build
    docker-compose --project-name rdrf -f fig-lettuce.yml up
}

selenium() {
    mkdir -p data/selenium
    chmod o+rwx data/selenium
    find ./definitions -name "*.yaml" -exec cp "{}" data/selenium \;

    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    docker-compose --project-name rdrf -f fig-selenium.yml rm --force
    docker-compose --project-name rdrf -f fig-selenium.yml build
    docker-compose --project-name rdrf -f fig-selenium.yml up
}

registry_specific_tests() {
    for yaml_file in definitions/registries/*.yaml; do
        echo "running registry specific tests for $yaml_file ( if any)"
    done
}


start() {
    mkdir -p data/dev
    chmod o+rwx data/dev

    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    docker-compose --project-name rdrf up
}


unit_tests() {
    mkdir -p data/tests
    chmod o+rwx data/tests

    make_virtualenv
    . ${VIRTUALENV}/bin/activate

    docker-compose --project-name rdrf -f fig-test.yml rm --force
    docker-compose --project-name rdrf -f fig-test.yml build
    docker-compose --project-name rdrf -f fig-test.yml up
}


make_virtualenv() {
    which virtualenv > /dev/null
    if [ ! -e ${VIRTUALENV} ]; then
        virtualenv ${VIRTUALENV}
    fi

    pip install 'docker-compose<=1.6' --upgrade || true
}


pythonlint() {
    make_virtualenv
    ${VIRTUALENV}/bin/pip install 'flake8>=2.0,<2.1'
    ${VIRTUALENV}/bin/flake8 rdrf --exclude=migrations,selenium_test --ignore=E501 --count
}


jslint() {
    make_virtualenv
    ${VIRTUALENV}/bin/pip install 'closure-linter==2.3.13'

    JSFILES=`ls rdrf/rdrf/static/js/*.js | grep -v "\.min\."`
    EXCLUDES='-x rdrf/rdrf/static/js/gallery.js,rdrf/rdrf/static/js/ie_select.js,rdrf/rdrf/static/js/jquery.bootgrid.js,rdrf/rdrf/static/js/nv.d3.js'
    for JS in $JSFILES
    do
        ${VIRTUALENV}/bin/gjslint ${EXCLUDES} --disable 0131,0110 --max_line_length 100 --nojsdoc $JS
    done
}


case ${ACTION} in
pythonlint)
    pythonlint
    ;;
jslint)
    jslint
    ;;
dockerbuild)
    dockerbuild
    ;;
rpmbuild)
    rpmbuild
    ;;
rpm_publish)
    ci_ssh_agent
    rpm_publish
    ;;
ci_staging)
    ci_ssh_agent
    ci_staging
    ;;
start)
    start
    ;;
unit_tests)
    unit_tests
    ;;
selenium)
    selenium
    ;;
lettuce)
    lettuce
    ;;
registry_specific_tests)
    registry_specific_tests
    ;;
*)
    usage
esac
