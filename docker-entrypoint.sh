#!/bin/bash


# wait for a given host:port to become available
#
# $1 host
# $2 port
function dockerwait {
    while ! exec 6<>/dev/tcp/"$1"/"$2"; do
        warn "$(date) - waiting to connect $1 $2"
        sleep 5
    done
    success "$(date) - connected to $1 $2"

    exec 6>&-
    exec 6<&-
}


function info () {
    printf "\r  [\033[00;34mINFO\033[0m] %s\n" "$1"
}


function warn () {
    printf "\r  [\033[00;33mWARN\033[0m] %s\n" "$1"
}


function success () {
    printf "\r\033[2K  [\033[00;32m OK \033[0m] %s\n" "$1"
}


function fail () {
    printf "\r\033[2K  [\033[0;31mFAIL\033[0m] %s\n" "$1"
    echo ''
    exit 1
}


# wait for services to become available
# this prevents race conditions using fig
function wait_for_services {
    if [[ "$WAIT_FOR_DB" ]] ; then
        dockerwait "$DBSERVER" "$DBPORT"
    fi
    if [[ "$WAIT_FOR_CLINICAL_DB" ]] ; then
        dockerwait "$CLINICAL_DBSERVER" "$CLINICAL_DBPORT"
    fi
    if [[ "$WAIT_FOR_REPORTING_DB" ]] ; then
        dockerwait "$REPORTING_DBSERVER" "$REPORTING_DBPORT"
    fi
    if [[ "$WAIT_FOR_CACHE" ]] ; then
        dockerwait "$CACHESERVER" "$CACHEPORT"
    fi
    if [[ "$WAIT_FOR_RUNSERVER" ]] ; then
        dockerwait "$RUNSERVER" "$RUNSERVERPORT"
    fi
    if [[ "$WAIT_FOR_HOST_PORT" ]]; then
        dockerwait "$DOCKER_ROUTE" "$WAIT_FOR_HOST_PORT"
    fi
    if [[ "$WAIT_FOR_UWSGI" ]] ; then
        dockerwait "$UWSGISERVER" "$UWSGIPORT"
    fi
}


function defaults {
    : "${DBSERVER:=db}"
    : "${DBPORT:=5432}"
    : "${DBUSER:=webapp}"
    : "${DBNAME:=${DBUSER}}"
    : "${DBPASS:=${DBUSER}}"

    : "${CLINICAL_DBSERVER:=clinicaldb}"
    : "${CLINICAL_DBPORT:=5432}"
    : "${CLINICAL_DBUSER:=webapp}"
    : "${CLINICAL_DBNAME:=${CLINICAL_DBUSER}}"
    : "${CLINICAL_DBPASS:=${CLINICAL_DBUSER}}"
    
    : "${REPORTING_DBSERVER:=reportingdb}"
    : "${REPORTING_DBPORT:=5432}"
    : "${REPORTING_DBUSER:=webapp}"
    : "${REPORTING_DBNAME:=${REPORTING_DBUSER}}"
    : "${REPORTING_DBPASS:=${REPORTING_DBUSER}}"

    : "${DOCKER_ROUTE:=$(/sbin/ip route|awk '/default/ { print $3 }')}"

    : "${UWSGISERVER:=uwsgi}"
    : "${UWSGIPORT:=9000}"
    : "${UWSGI_OPTS:=/app/uwsgi/docker.ini}"
    : "${RUNSERVER:=runserver}"
    : "${RUNSERVERPORT:=8000}"
    : "${RUNSERVER_CMD:=runserver}"
    : "${CACHESERVER:=cache}"
    : "${CACHEPORT:=11211}"
    : "${MEMCACHE:=${CACHESERVER}:${CACHEPORT}}"

    # variables to control where tests will look for the app (aloe via selenium hub)
    : "${TEST_APP_SCHEME:=http}"
    : "${TEST_APP_HOST:=runservertest}"
    : "${TEST_APP_PORT:=8000}"
    : "${TEST_APP_PATH:=/}"
    : "${TEST_APP_URL:=${TEST_APP_SCHEME}://${TEST_APP_HOST}:${TEST_APP_PORT}${TEST_APP_PATH}}"
    #: "${TEST_BROWSER:=chrome}"
    : "${TEST_BROWSER:=firefox}"
    : "${TEST_WAIT:=30}"
    : "${TEST_SELENIUM_HUB:=http://hub:4444/wd/hub}"

    : "${DJANGO_FIXTURES:=none}"

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MEMCACHE DOCKER_ROUTE
    export CLINICAL_DBSERVER CLINICAL_DBPORT CLINICAL_DBUSER CLINICAL_DBNAME CLINICAL_DBPASS
    export REPORTING_DBSERVER REPORTING_DBPORT REPORTING_DBUSER REPORTING_DBNAME REPORTING_DBPASS
    export TEST_APP_URL TEST_APP_SCHEME TEST_APP_HOST TEST_APP_PORT TEST_APP_PATH TEST_BROWSER TEST_WAIT TEST_SELENIUM_HUB
    export DJANGO_FIXTURES
}


function _django_check_deploy {
    info "running check --deploy"
    set -x
    django-admin.py check --deploy --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-check.log
    set +x
}


function _django_migrate {
    info "running migrate"
    set -x
    django-admin.py migrate --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-migrate.log
    django-admin.py migrate --database=clinical --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-migrate-clinical.log
    django-admin.py update_permissions --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-permissions.log
    set +x
}


function _django_collectstatic {
    info "running collectstatic"
    set -x
    django-admin.py collectstatic --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-collectstatic.log
    set +x
}


function _django_test_fixtures {
    info 'loading test (iprestrict permissive) fixture'
    set -x
    django-admin.py init iprestrict_permissive
    django-admin.py reload_rules
    set +x
}


function _django_dev_fixtures {
    info "loading DEV fixture"
    set -x
    django-admin.py init DEV
    django-admin.py reload_rules
    set +x
}


function _rdrf_import_grdr {
    info "importing grdr registry"
    set -x
    django-admin.py import_registry --file=/app/grdr.yaml
    set +x
}


function _django_fixtures {
    if [ "${DJANGO_FIXTURES}" = 'test' ]; then
        _django_test_fixtures
    fi

    if [ "${DJANGO_FIXTURES}" = 'dev' ]; then
        _django_dev_fixtures
    fi
}


function _runserver() {
    : "${RUNSERVER_OPTS=${RUNSERVER_CMD} 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}}"

    _django_collectstatic
    _django_migrate
    _django_fixtures

    info "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"
    set -x
    # shellcheck disable=SC2086
    exec django-admin.py ${RUNSERVER_OPTS}
}


function _aloe() {
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"_test
    shift
    set -x
    exec django-admin.py harvest --with-xunit --xunit-file="${WRITABLE_DIRECTORY}"/tests.xml --verbosity=3 "$@"
}


trap exit SIGHUP SIGINT SIGTERM
defaults
env | grep -iv PASS | sort
wait_for_services

# prod uwsgi entrypoint
if [ "$1" = 'uwsgi' ]; then
    info "[Run] Starting prod uwsgi"

    _django_collectstatic
    _django_migrate
    _django_check_deploy

    set -x
    exec uwsgi --die-on-term --ini "${UWSGI_OPTS}"
fi

# local and test uwsgi entrypoint
if [ "$1" = 'uwsgi_local' ]; then
    info "[Run] Starting local uwsgi"

    _django_collectstatic
    _django_migrate
    _django_fixtures
    _django_check_deploy

    set -x
    exec uwsgi --die-on-term --ini "${UWSGI_OPTS}"
fi

# runserver entrypoint
if [ "$1" = 'runserver' ]; then
    info "[Run] Starting runserver"
    _runserver
fi

# runserver_plus entrypoint
if [ "$1" = 'runserver_plus' ]; then
    info "[Run] Starting runserver_plus"
    RUNSERVER_CMD=runserver_plus
    _runserver
fi

# grdr entrypoint
if [ "$1" = 'grdr' ]; then
    info "[Run] Starting runserver_plus with GRDR data elements"

    _django_collectstatic
    _django_migrate
    _django_fixtures
    _rdrf_import_grdr

    RUNSERVER_CMD=runserver_plus
    _runserver
fi

# runtests entrypoint
if [ "$1" = 'runtests' ]; then
    info "[Run] Starting tests"
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"_test

    set -x
    single_test="$2"

    if [ "$single_test" != "" ]; then
	exec django-admin.py test --noinput -v 3 "$single_test"

    else
	exec django-admin.py test --noinput -v 3 rdrf
    fi
fi

# aloe entrypoint
if [ "$1" = 'aloe' ]; then
    info "[Run] Starting aloe"
    cd /app/rdrf/rdrf/testing/behaviour || exit
    _aloe "$@"
fi

# allow execution of a management command
if [ "$1" = "management-command" ]; then
    command_line="django-admin.py $2"
    exec $command_line
fi

warn "[RUN]: Builtin command not provided [tarball|aloe|runtests|runserver|runserver_plus|uwsgi|uwsgi_local]"
info "[RUN]: $*"

set -x
# shellcheck disable=SC2086 disable=SC2048
exec "$@"
