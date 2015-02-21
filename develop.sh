#!/bin/bash
#
TOPDIR=$(cd `dirname $0`; pwd)


# break on error
set -e 

ACTION="$1"

PROJECT_NAME='rdrf'
VIRTUALENV="${TOPDIR}/virt_${PROJECT_NAME}"
AWS_STAGING_INSTANCE='ccg_syd_nginx_staging'
TARGET_DIR="/usr/local/src/${PROJECT_NAME}"
TESTING_MODULES="pyvirtualdisplay nose selenium lettuce lettuce_webdriver"
MODULES="psycopg2==2.5.2 Werkzeug flake8 ${TESTING_MODULES}"
PIP_OPTS='--download-cache ~/.pip/cache --process-dependency-links'


usage() {
    echo 'Usage ./develop.sh (test|pythonlint|jslint|rpmbuild|rpm_publish|unit_tests|selenium|ci_staging)'
}


settings() {
    export DJANGO_SETTINGS_MODULE="rdrf.settings"
}


# ssh setup, make sure our ccg commands can run in an automated environment
ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    . /tmp/agent.env.sh
    ssh-add ~/.ssh/ccg-syd-staging-2014.pem
}


# build RPMs
rpmbuild() {
    mkdir -p data/rpmbuild
    chmod o+rwx data/rpmbuild

    make_virtualenv
    . ${VIRTUALENV}/bin/activate
    pip install fig

    fig --project-name yabi -f fig-rpmbuild.yml up
}

# publish rpms 
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
    ccg ${AWS_STAGING_INSTANCE} drun:'docker-untagged || true'
}


selenium() {
    mkdir -p data/selenium
    chmod o+rwx data/selenium

    make_virtualenv
    . ${VIRTUALENV}/bin/activate
    pip install fig

    fig -f fig-selenium.yml up
}


unit_tests() {
    mkdir -p data/tests
    chmod o+rwx data/tests

    make_virtualenv
    . ${VIRTUALENV}/bin/activate
    pip install fig

    fig -f fig-test.yml up
}

make_virtualenv() {
    # check requirements
    which virtualenv > /dev/null
    virtualenv ${VIRTUALENV}
}


# lint using flake8
pythonlint() {
    make_virtualenv
    ${VIRTUALENV}/bin/pip install 'flake8>=2.0,<2.1'
    ${VIRTUALENV}/bin/flake8 rdrf/rdrf --exclude=migrations --ignore=E501 --count
}

# lint js, assumes closure compiler
jslint() {
    make_virtualenv
    ${VIRTUALENV}/bin/pip install 'closure-linter==2.3.13'

    JSFILES="rdrf/rdrf/static/js/*.js"
    for JS in $JSFILES
    do
        ${VIRTUALENV}/bin/gjslint --disable 0131 --max_line_length 100 --nojsdoc $JS
    done

}


# run the tests using nose
nosetests() {
    source virt_rdrf/bin/activate
    virt_rdrf/bin/nosetests --with-xunit --xunit-file=tests.xml -v -w rdrf
}


# run the tests using django-admin.py
djangotests() {
    source virt_rdrf/bin/activate
    virt_rdrf/bin/django-admin.py test rdrf --noinput
}

# nose collect, untested
nose_collect() {
    source virt_rdrf/bin/activate
    virt_rdrf/bin/nosetests -v -w rdrf --collect-only
}


# tests
runtest() {
    #nosetests
    djangotests
}


case ${ACTION} in
test)
    settings
    runtest
    ;;
pythonlint)
    pythonlint
    ;;
jslint)
    jslint
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
unit_tests)
    unit_tests
    ;;
selenium)
    selenium
    ;;
*)
    usage
esac
