#!/bin/bash
#
TOPDIR=$(cd `dirname $0`; pwd)
VIRTUALENV="${TOPDIR}/virt_${PROJECT_NAME}"


# break on error
set -e 
set -x

ACTION="$1"

PROJECT_NAME='rdrf'
AWS_STAGING_INSTANCE='ccg_syd_nginx_staging'
TARGET_DIR="/usr/local/src/${PROJECT_NAME}"
CLOSURE="/usr/local/closure/compiler.jar"
TESTING_MODULES="pyvirtualdisplay nose selenium lettuce lettuce_webdriver"
MODULES="psycopg2==2.5.2 Werkzeug flake8 ${TESTING_MODULES}"
PIP_OPTS='--download-cache ~/.pip/cache --process-dependency-links'


usage() {
    echo 'Usage ./develop.sh (test|ci_lint|rpmbuild|rpm_publish|ci_staging|ci_staging_selenium|ci_staging_fixture|ci_staging_tests)'
}


settings() {
    export DJANGO_SETTINGS_MODULE="rdrf.settings"
}


# ssh setup, make sure our ccg commands can run in an automated environment
ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    source /tmp/agent.env.sh
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
    ccg ${AWS_STAGING_INSTANCE} drun:'docker-untagged'
}

#Preload fixtures from JSON file
ci_staging_fixture() {
    # todo
    exit -1

    local result=`ccg ${AWS_STAGING_INSTANCE} dsudo:'cat /tmp/rdrfsentinel || exit 0' | grep 'out: loaded' | awk  '{print $3;}'`
    echo "content of sentinel file=[$result]"
    if [ "$result" != "loaded" ]; then
        echo "/tmp/rdrfsentinel file does not exist - loading fixtures ..."
        ccg ${AWS_STAGING_INSTANCE} dsudo:'rdrf load_fixture --file\=rdrf.json'
        ccg ${AWS_STAGING_INSTANCE} dsudo:'rdrf load_fixture --file\=users.json'
        ccg ${AWS_STAGING_INSTANCE} dsudo:'echo loaded > /tmp/rdrfsentinel'
    else
        echo "Fixtures already loaded as sentinel file /tmp/rdrfsentinel exists - No fixtures were loaded"
    fi
}

# staging selenium test
ci_staging_selenium() {
    # todo
    exit -1

    ccg ${AWS_STAGING_INSTANCE} dsudo:"pip2.7 install ${PIP_OPTS} ${TESTING_MODULES}"
    ccg ${AWS_STAGING_INSTANCE} dsudo:'dbus-uuidgen --ensure'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'chown apache:apache /var/www'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum --enablerepo\=ccg-testing clean all'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum install rdrf -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'killall httpd || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'service httpd start'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'echo https://staging.ccgapps.com.au/rdrf-staging > /tmp/rdrf_site_url'
    #ccg ${AWS_STAGING_INSTANCE} dsudo:'echo http://localhost/rdrf > /tmp/rdrf_site_url'
    ccg ${AWS_STAGING_INSTANCE} drunbg:"Xvfb -ac \:0"
    ccg ${AWS_STAGING_INSTANCE} dsudo:'mkdir -p lettuce && chmod o+w lettuce'
    sleep 5
    ccg ${AWS_STAGING_INSTANCE} dsudo:"cd lettuce && env DISPLAY\=\:0 rdrf run_lettuce --with-xunit --xunit-file\=/tmp/tests.xml || true"
    ccg ${AWS_STAGING_INSTANCE} dsudo:'rm /tmp/rdrf_site_url'
    ccg ${AWS_STAGING_INSTANCE} getfile:/tmp/tests.xml,./
}

# run tests on staging
ci_staging_tests() {
    # todo
    exit -1

    REMOTE_TEST_DIR=/tmp
    # Grant permission to create a test database.
    DATABASE_USER=rdrf
    ccg ${AWS_STAGING_INSTANCE} dsudo:"su postgres -c \"psql -c 'ALTER ROLE ${DATABASE_USER} CREATEDB;'\""

    # This is the command which runs manage.py with the correct environment
    DJANGO_ADMIN="rdrf"

    # Run tests
    ccg ${AWS_STAGING_INSTANCE} dsudo:"cd ${REMOTE_TEST_DIR} && ${DJANGO_ADMIN} test rdrf"
}

make_virtualenv() {
    # check requirements
    which virtualenv-2.7 > /dev/null
    virtualenv-2.7 ${VIRTUALENV}
    ${VIRTUALENV}/bin/pip install ${PIP_OPTS} --upgrade 'pip>=1.5,<1.6'
}


# lint using flake8
lint() {
    virt_rdrf/bin/flake8 rdrf/rdrf --exclude=migrations --ignore=E501 --count
}

# lint js, assumes closure compiler
jslint() {
    JSFILES="rdrf/rdrf/rdrf/static/js/*.js"
    for JS in $JSFILES
    do
        ${VIRTUALENV}/bin/gjslint --disable 0131 --max_line_length 100 --nojsdoc $JS
    done

}

# lint both Python and JS on CI server
ci_lint() {
    make_virtualenv
    ${VIRTUALENV}/bin/pip install 'closure-linter==2.3.13' 'flake8>=2.0,<2.1'
    lint
    jslint
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
pythonversion)
    pythonversion
    ;;
pipfreeze)
    pipfreeze
    ;;
test)
    settings
    runtest
    ;;
ci_lint)
    ci_lint
    ;;
lint)
    lint
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
ci_staging_selenium)
    ci_ssh_agent
    ci_staging_selenium
    ;;
ci_staging_fixture)
    ci_ssh_agent
    ci_staging_fixture
    ;;
ci_staging_tests)
    ci_ssh_agent
    ci_staging_tests
    ;;
*)
    usage
esac
