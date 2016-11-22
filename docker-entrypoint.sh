#!/bin/bash


# wait for a given host:port to become available
#
# $1 host
# $2 port
function dockerwait {
    while ! exec 6<>/dev/tcp/$1/$2; do
        echo "$(date) - waiting to connect $1 $2"
        sleep 5
    done
    echo "$(date) - connected to $1 $2"

    exec 6>&-
    exec 6<&-
}


# wait for services to become available
# this prevents race conditions using fig
function wait_for_services {
    if [[ "$WAIT_FOR_DB" ]] ; then
        dockerwait $DBSERVER $DBPORT
    fi
    if [[ "$WAIT_FOR_CLINICAL_DB" ]] ; then
        dockerwait $CLINICAL_DBSERVER $CLINICAL_DBPORT
    fi
    if [[ "$WAIT_FOR_CACHE" ]] ; then
        dockerwait $CACHESERVER $CACHEPORT
    fi
    if [[ "$WAIT_FOR_RUNSERVER" ]] ; then
        dockerwait $RUNSERVER $RUNSERVERPORT
    fi
    if [[ "$WAIT_FOR_MONGO" ]] ; then
        dockerwait $MONGOSERVER $MONGOPORT
    fi
    if [[ "$WAIT_FOR_HOST_PORT" ]]; then
        dockerwait $DOCKER_ROUTE $WAIT_FOR_HOST_PORT
    fi
    if [[ "$WAIT_FOR_UWSGI" ]] ; then
        dockerwait $UWSGISERVER $UWSGIPORT
    fi
}


function defaults {
    : ${DBSERVER:="db"}
    : ${DBPORT:="5432"}
    : ${DBUSER:="webapp"}
    : ${DBNAME:="${DBUSER}"}
    : ${DBPASS:="${DBUSER}"}

    : ${CLINICAL_DBSERVER:="clinicaldb"}
    : ${CLINICAL_DBPORT:="5432"}
    : ${CLINICAL_DBUSER:="webapp"}
    : ${CLINICAL_DBNAME:="${CLINICAL_DBUSER}"}
    : ${CLINICAL_DBPASS:="${CLINICAL_DBUSER}"}

    : ${DOCKER_ROUTE:=$(/sbin/ip route|awk '/default/ { print $3 }')}

    : ${UWSGISERVER:="uwsgi"}
    : ${UWSGIPORT:="9000"}
    : ${RUNSERVER:="web"}
    : ${RUNSERVERPORT:="8000"}
    : ${CACHESERVER:="cache"}
    : ${CACHEPORT:="11211"}
    : ${MEMCACHE:="${CACHESERVER}:${CACHEPORT}"}
    : ${MONGOSERVER:="mongo"}
    : ${MONGOPORT:="27017"}

    # variables to control where tests will look for the app (aloe via selenium hub)
    : ${TEST_APP_SCHEME:="http"}
    : ${TEST_APP_HOST:=${DOCKER_ROUTE}}
    : ${TEST_APP_PORT:="18000"}
    : ${TEST_APP_PATH:="/"}
    : ${TEST_APP_URL:="${TEST_APP_SCHEME}://${TEST_APP_HOST}:${TEST_APP_PORT}${TEST_APP_PATH}"}
    #: ${TEST_BROWSER:="chrome"}
    : ${TEST_BROWSER:="firefox"}
    : ${TEST_WAIT:="30"}
    : ${TEST_SELENIUM_HUB:="http://hub:4444/wd/hub"}

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MONGOSERVER MONGOPORT MEMCACHE DOCKER_ROUTE
    export CLINICAL_DBSERVER CLINICAL_DBPORT CLINICAL_DBUSER CLINICAL_DBNAME CLINICAL_DBPASS
    export TEST_APP_URL TEST_APP_SCHEME TEST_APP_HOST TEST_APP_PORT TEST_APP_PATH TEST_BROWSER TEST_WAIT TEST_SELENIUM_HUB
}


function _django_check_deploy {
    echo "running check --deploy"
    django-admin.py check --deploy --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee ${LOG_DIRECTORY}/uwsgi-check.log
}


function _django_migrate {
    echo "running migrate"
    django-admin.py migrate --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee ${LOG_DIRECTORY}/uwsgi-migrate.log
    django-admin.py migrate --database=clinical --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee ${LOG_DIRECTORY}/uwsgi-migrate-clinical.log
    django-admin.py update_permissions --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee ${LOG_DIRECTORY}/uwsgi-permissions.log
}


function _django_collectstatic {
    echo "running collectstatic"
    django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee ${LOG_DIRECTORY}/uwsgi-collectstatic.log
}

function _django_iprestrict_permissive_fixtures {
    echo "loading iprestrict permissive fixture"
    django-admin.py init iprestrict_permissive
    django-admin.py reloadrules
}

function _django_dev_fixtures {
    echo "loading DEV fixture"
    django-admin.py init DEV
    django-admin.py reloadrules
}

function _rdrf_import_grdr {
    echo "importing grdr registry"
    django-admin.py import_registry --file=/app/grdr.yaml
}

function _django_fixtures {
    if [ "${DEPLOYMENT}" = 'test' ]; then
        _django_iprestrict_permissive_fixtures
    fi

    if [ "${DEPLOYMENT}" = 'dev' ]; then
        _django_dev_fixtures
    fi
}


function _runserver() {
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_fixtures

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
}



trap exit SIGHUP SIGINT SIGTERM
defaults
env | grep -iv PASS | sort
wait_for_services

# prod uwsgi entrypoint
if [ "$1" = 'uwsgi' ]; then
    echo "[Run] Starting prod uwsgi"

    : ${UWSGI_OPTS="/app/uwsgi/docker.ini"}
    echo "UWSGI_OPTS is ${UWSGI_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_check_deploy

    exec uwsgi --die-on-term --ini ${UWSGI_OPTS}
fi

# local and test uwsgi entrypoint
if [ "$1" = 'uwsgi_local' ]; then
    echo "[Run] Starting local uwsgi"

    : ${UWSGI_OPTS="/app/uwsgi/docker.ini"}
    echo "UWSGI_OPTS is ${UWSGI_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_fixtures
    _django_check_deploy

    exec uwsgi --die-on-term --ini ${UWSGI_OPTS}
fi

# runserver entrypoint
if [ "$1" = 'runserver' ]; then
    echo "[Run] Starting runserver"

    : ${RUNSERVER_OPTS="runserver 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    _runserver
fi

# runserver_plus entrypoint
if [ "$1" = 'runserver_plus' ]; then
    echo "[Run] Starting runserver_plus"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    _runserver
fi

# grdr entrypoint
if [ "$1" = 'grdr' ]; then
    echo "[Run] Starting runserver with GRDR data elements"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_fixtures
    _rdrf_import_grdr

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
fi

# runtests entrypoint
if [ "$1" = 'runtests' ]; then
    echo "[Run] Starting tests"
    exec django-admin.py test --noinput -v 3 rdrf
fi

# aloe entrypoint
if [ "$1" = 'aloe' ]; then
    echo "[Run] Starting aloe"

    # stellar config needs to be in PWD at runtime for aloe tests
    if [ ! -f ${PWD}/stellar.yaml ]; then
        cp /app/stellar.yaml ${PWD}/stellar.yaml
    fi
    export DJANGO_SETTINGS_MODULE=rdrf.settings_test
    shift
    cd /app/rdrf
    exec django-admin.py harvest --with-xunit --xunit-file=${WRITABLE_DIRECTORY}/tests.xml --verbosity=3 $@
fi

echo "[RUN]: Builtin command not provided [tarball|aloe|runtests|runserver|uwsgi|uwsgi_fixtures]"
echo "[RUN]: $@"

exec "$@"
