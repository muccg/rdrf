#!/bin/bash
#

# break on error
set -e 

ACTION="$1"
REGISTRY="$2"

PROJECT_NAME='disease_registry'
AWS_BUILD_INSTANCE='aws_rpmbuild_centos6'
AWS_STAGING_INSTANCE='aws-syd-registry-staging'
TARGET_DIR="/usr/local/src/${PROJECT_NAME}"
CLOSURE="/usr/local/closure/compiler.jar"
TESTING_MODULES="pyvirtualdisplay nose selenium"
MODULES="psycopg2==2.4.6 Werkzeug flake8 ${TESTING_MODULES}"
PIP_OPTS='--download-cache ~/.pip/cache --index-url=https://restricted.crate.io'


function usage() {
    echo 'Usage ./develop.sh (test|lint|jslint|start|install|clean|purge|pipfreeze|pythonversion|dropdb|ci_remote_build|ci_remote_destroy|ci_rpm_publish|ci_staging|ci_staging_selenium|ci_staging_tests) (dd|dmd|dm1|sma|fshd)'
}


function registry_needed() {
    if ! test ${REGISTRY}; then
        usage
        exit 1
    fi
}


function settings() {
    registry_needed
    export DJANGO_SETTINGS_MODULE="${REGISTRY}.settings"
}


# ssh setup, make sure our ccg commands can run in an automated environment
function ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    source /tmp/agent.env.sh
    ssh-add ~/.ssh/ccg-syd-staging.pem
}


# build RPMs on a remote host from ci environment
function ci_remote_build() {
    registry_needed

    time ccg ${AWS_BUILD_INSTANCE} puppet
    time ccg ${AWS_BUILD_INSTANCE} shutdown:50

    EXCLUDES="('bootstrap'\, '.hg*'\, 'virt*'\, '*.log'\, '*.rpm'\, 'build'\, 'dist'\, '*/build'\, '*/dist')"
    SSH_OPTS="-o StrictHostKeyChecking\=no"
    RSYNC_OPTS="-l"
    time ccg ${AWS_BUILD_INSTANCE} rsync_project:local_dir=./,remote_dir=${TARGET_DIR}/,ssh_opts="${SSH_OPTS}",extra_opts="${RSYNC_OPTS}",exclude="${EXCLUDES}",delete=True
    time ccg ${AWS_BUILD_INSTANCE} build_rpm:centos/${REGISTRY}/${REGISTRY}.spec,src=${TARGET_DIR}

    mkdir -p build
    ccg ${AWS_BUILD_INSTANCE} getfile:rpmbuild/RPMS/x86_64/${REGISTRY}*.rpm,build/
}


# publish rpms 
function ci_rpm_publish() {
    registry_needed
    time ccg publish_testing_rpm:build/${REGISTRY}*.rpm,release=6
}


# destroy our ci build server
function ci_remote_destroy() {
    ccg ${AWS_BUILD_INSTANCE} destroy
}


# puppet up staging which will install the latest rpm for each registry
function ci_staging() {
    ccg ${AWS_STAGING_INSTANCE} boot
    ccg ${AWS_STAGING_INSTANCE} puppet
    ccg ${AWS_STAGING_INSTANCE} shutdown:120
}


# staging seleinium test
function ci_staging_selenium() {
    ccg ${AWS_STAGING_INSTANCE} dsudo:'dbus-uuidgen --ensure'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'chown apache:apache /var/www'


    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum remove dmd dd dm1 sma fshd -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum --enablerepo\=ccg-testing clean all'

    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum install dmd -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'killall httpd || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'service httpd start'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'echo http://localhost/dmd > /tmp/dmd_site_url'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'dmd run_lettuce --app-name dmd --with-xunit --xunit-file\=/tmp/tests-dmd.xml || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum remove dmd -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'rm /tmp/dmd_site_url'
    
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum install sma -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'killall httpd || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'service httpd start'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'echo http://localhost/sma > /tmp/sma_site_url'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'sma run_lettuce --app-name sma --with-xunit --xunit-file\=/tmp/tests-sma.xml || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum remove sma -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'rm /tmp/sma_site_url'
    
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum install dm1 -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'killall httpd || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'service httpd start'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'echo http://localhost/dm1 > /tmp/dm1_site_url'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'dm1 run_lettuce --app-name dm1 --with-xunit --xunit-file\=/tmp/tests-dm1.xml || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum remove dm1 -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'rm /tmp/dm1_site_url'
    
    ccg ${AWS_STAGING_INSTANCE} dsudo:'yum install dd -y'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'killall httpd || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'service httpd start'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'echo http://localhost/dd > /tmp/dd_site_url'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'registrydd run_lettuce --app-name dd --with-xunit --xunit-file\=/tmp/tests-dd.xml || true'
    ccg ${AWS_STAGING_INSTANCE} dsudo:'rm /tmp/dd_site_url'

    ccg ${AWS_STAGING_INSTANCE} getfile:/tmp/tests-dmd.xml,./
    ccg ${AWS_STAGING_INSTANCE} getfile:/tmp/tests-sma.xml,./
    ccg ${AWS_STAGING_INSTANCE} getfile:/tmp/tests-dm1.xml,./
    ccg ${AWS_STAGING_INSTANCE} getfile:/tmp/tests-dd.xml,./
}

# gets the manage.py command for a registry
function django_admin() {
    case $1 in
        dd)
            echo "registrydd"
            ;;
        *)
            echo $1
            ;;
    esac
}

# run tests on staging
function ci_staging_tests() {
    registry_needed

    # /tmp is used for test results because the apache user has
    # permission to write there.
    REMOTE_TEST_DIR=/tmp
    REMOTE_TEST_RESULTS=${REMOTE_TEST_DIR}/tests.xml

    # Grant permission to create a test database.
    DATABASE_USER=registryapp
    ccg ${AWS_STAGING_INSTANCE} dsudo:"su postgres -c \"psql -c 'ALTER ROLE ${DATABASE_USER} CREATEDB;'\""

    # This is the command which runs manage.py with the correct environment
    DJANGO_ADMIN=$(django_admin ${REGISTRY})

    # Run tests, collect results
    TEST_LIST="${REGISTRY}.${REGISTRY}.tests"
    ccg ${AWS_STAGING_INSTANCE} drunbg:"Xvfb \:0"
    ccg ${AWS_STAGING_INSTANCE} dsudo:"cd ${REMOTE_TEST_DIR} && env DISPLAY\=\:0 dbus-launch ${DJANGO_ADMIN} test --noinput --with-xunit --xunit-file\=${REMOTE_TEST_RESULTS} --liveserver\=localhost\:8082\,8090-8100\,9000\-9200\,7041 ${TEST_LIST} || true"
    ccg ${AWS_STAGING_INSTANCE} getfile:${REMOTE_TEST_RESULTS},./
}


# lint using flake8
function lint() {
    registry_needed
    virt_${REGISTRY}/bin/flake8 ${REGISTRY} --ignore=E501 --count 
}


# lint js, assumes closure compiler
function jslint() {
    registry_needed
    JSFILES="${REGISTRY}/${REGISTRY}/${REGISTRY}/static/js/*.js"
    for JS in $JSFILES
    do
        java -jar ${CLOSURE} --js $JS --js_output_file output.js --warning_level DEFAULT --summary_detail_level 3
    done
}


# some db commands I use
function dropdb() {
    registry_needed
    # assumes postgres, user registryapp exists, appropriate pg_hba.conf
    echo "Drop the dev database manually:"
    echo "psql -aeE -U postgres -c \"SELECT pg_terminate_backend(pg_stat_activity.procpid) FROM pg_stat_activity where pg_stat_activity.datname = '${REGISTRY}'\" && psql -aeE -U postgres -c \"alter user registryapp createdb;\" template1 && psql -aeE -U registryapp -c \"drop database ${REGISTRY}\" template1 && psql -aeE -U registryapp -c \"create database ${REGISTRY};\" template1"
}


# run the tests using nose
function nosetests() {
    registry_needed
    source virt_${REGISTRY}/bin/activate
    virt_${REGISTRY}/bin/nosetests --with-xunit --xunit-file=tests.xml -v -w ${REGISTRY}
}


# run the tests using django-admin.py
function djangotests() {
    registry_needed
    source virt_${REGISTRY}/bin/activate
    virt_${REGISTRY}/bin/django-admin.py test ${REGISTRY} --noinput
}

# nose collect, untested
function nose_collect() {
    registry_needed
    source virt_${REGISTRY}/bin/activate
    virt_${REGISTRY}/bin/nosetests -v -w ${REGISTRY} --collect-only
}


# install virt for project
function installapp() {
    registry_needed
    # check requirements
    which virtualenv >/dev/null

    echo "Install ${REGISTRY}"
    virtualenv --system-site-packages virt_${REGISTRY}
    pushd ${REGISTRY}
    ../virt_${REGISTRY}/bin/pip install ${PIP_OPTS} -e .
    popd
    virt_${REGISTRY}/bin/pip install ${PIP_OPTS} ${MODULES}

    mkdir -p ${HOME}/bin
    ln -sf ${VIRTUALENV}/bin/python ${HOME}/bin/vpython-${REGISTRY}
}


# django syncdb, migrate and collect static
function syncmigrate() {
    registry_needed
    echo "syncdb"
    virt_${REGISTRY}/bin/django-admin.py syncdb --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> syncdb-develop.log
    echo "migrate"
    virt_${REGISTRY}/bin/django-admin.py migrate --settings=${DJANGO_SETTINGS_MODULE} 1> migrate-develop.log
    echo "collectstatic"
    virt_${REGISTRY}/bin/django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> collectstatic-develop.log
}

# chooses a tcp port number for the debug server
function port() {
    # this could be an associative array, but they aren't compatible
    # with bash3
    case $1 in
        dmd)
            echo "8001"
            ;;
        sma)
            echo "8002"
            ;;
        dm1)
            echo "8003"
            ;;
        dd)
            echo "8004"
            ;;
        fshd)
            echo "8005"
            ;;
    esac
}

# start runserver
function startserver() {
    registry_needed
    virt_${REGISTRY}/bin/django-admin.py runserver_plus 0.0.0.0:$(port ${REGISTRY})
}


# debug for ci
function pythonversion() {
    registry_needed
    virt_${REGISTRY}/bin/python -V
}


# debug for ci
function pipfreeze() {
    registry_needed
    virt_${REGISTRY}/bin/pip freeze
}


# remove pyc
function clean() {
    registry_needed
    find ${REGISTRY} -name "*.pyc" -exec rm -rf {} \;
}


# clean, delete virts and logs
function purge() {
    registry_needed
    clean
    rm -rf virt_${REGISTRY}
    rm *.log
}


# tests
function runtest() {
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
lint)
    lint
    ;;
jslint)
    jslint
    ;;
syncmigrate)
    settings
    syncmigrate
    ;;
start)
    settings
    startserver
    ;;
install)
    settings
    installapp
    ;;
ci_remote_build)
    ci_ssh_agent
    ci_remote_build
    ;;
ci_remote_destroy)
    ci_ssh_agent
    ci_remote_destroy
    ;;
ci_rpm_publish)
    ci_ssh_agent
    ci_rpm_publish
    ;;
ci_staging)
    ci_ssh_agent
    ci_staging
    ;;
ci_staging_selenium)
    ci_ssh_agent
    ci_staging_selenium
    ;;
ci_staging_tests)
    ci_ssh_agent
    ci_staging_tests
    ;;
dropdb)
    dropdb
    ;;
clean)
    settings
    clean 
    ;;
purge)
    settings
    clean
    purge
    ;;
*)
    usage
esac
