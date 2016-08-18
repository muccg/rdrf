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
    if [[ "$WAIT_FOR_CACHE" ]] ; then
        dockerwait $CACHESERVER $CACHEPORT
    fi
    if [[ "$WAIT_FOR_RUNSERVER" ]] ; then
        dockerwait $RUNSERVER $RUNSERVERPORT
    fi
    if [[ "$WAIT_FOR_MONGO" ]] ; then
        dockerwait $MONGOSERVER $MONGOPORT
    fi

    if [[ "$WAIT_FOR_REPORTING" ]]; then
        dockerwait $REPORTINGDBSERVER $REPORTINGDBPORT
    fi

    if [[ "$WAIT_FOR_HOST_PORT" ]]; then
        dockerwait $DOCKER_ROUTE $WAIT_FOR_HOST_PORT
    fi
}


function defaults {
    : ${DBSERVER:="db"}
    : ${DBPORT:="5432"}
    : ${DBUSER:="webapp"}
    : ${DBNAME:="${DBUSER}"}
    : ${DBPASS:="${DBUSER}"}

    : ${DOCKER_ROUTE:=$(/sbin/ip route|awk '/default/ { print $3 }')}

    : ${REPORTINGDBSERVER:=${DBSERVER}}
    : ${REPORTINGDBPORT:=${DBPORT}}
    : ${REPORTINGDBUSER:=${DBUSER}}
    : ${REPORTINGDBNAME:=${REPORTINGDBUSER}}
    : ${REPORTINGDBPASS:=${REPORTINGDBUSER}}

    : ${RUNSERVER:="web"}
    : ${RUNSERVERPORT:="8000"}
    : ${SELENIUMRUNSERVERPORT:="18000"}
    : ${CACHESERVER:="cache"}
    : ${CACHEPORT:="11211"}
    : ${MEMCACHE:="${CACHESERVER}:${CACHEPORT}"}
    : ${MONGOSERVER:="mongo"}
    : ${MONGOPORT:="27017"}

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MONGOSERVER MONGOPORT MEMCACHE DOCKER_ROUTE
    export REPORTINGDBSERVER REPORTINGDBPORT REPORTINGDBUSER REPORTINGDBNAME REPORTINGDBPASS
}


function selenium_defaults {
    : ${RDRF_URL:="http://$DOCKER_ROUTE:$SELENIUMRUNSERVERPORT/"}
    #: ${RDRF_BROWSER:="*googlechrome"}
    : ${RDRF_BROWSER:="*firefox"}

    if [ ${DEPLOYMENT} = "prod" ]; then
        RDRF_URL="https://$DOCKER_ROUTE:8443/app/"
    fi

    # stellar config needs to be in PWD at runtime for lettuce tests
    if [ ! -f ${PWD}/stellar.yaml ]; then
        cp /app/stellar.yaml ${PWD}/stellar.yaml
    fi

    export RDRF_URL RDRF_BROWSER
}


function _django_check_deploy {
    echo "running check --deploy"
    django-admin.py check --deploy --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-check.log
}


function _django_migrate {
    echo "running migrate"
    django-admin.py migrate --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-migrate.log
    django-admin.py update_permissions --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-permissions.log
}


function _django_collectstatic {
    echo "running collectstatic"
    django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-collectstatic.log
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


trap exit SIGHUP SIGINT SIGTERM
defaults
env | grep -iv PASS | sort
wait_for_services

# prepare a tarball of build
if [ "$1" = 'releasetarball' ]; then
    echo "[Run] Preparing a release tarball"

    set -e
    cd /app
    rm -rf /app/*
    echo $GIT_TAG
    set -x
    git clone --depth=1 --branch=${GIT_TAG} ${PROJECT_SOURCE} .
    git ls-remote ${PROJECT_SOURCE} ${GIT_TAG} > .version

    # Note: Environment vars are used to control the behaviour of pip (use local devpi for instance)
    pip install -e rdrf
    set +x

    # create release tarball
    DEPS="/env /app/uwsgi /app/docker-entrypoint.sh /app/rdrf /app/scripts"
    cd /data
    exec tar -cpzf ${PROJECT_NAME}-${GIT_TAG}.tar.gz ${DEPS}
fi

# uwsgi entrypoint
if [ "$1" = 'uwsgi' ]; then
    echo "[Run] Starting uwsgi"

    : ${UWSGI_OPTS="/app/uwsgi/docker.ini"}
    echo "UWSGI_OPTS is ${UWSGI_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_check_deploy

    exec uwsgi --die-on-term --ini ${UWSGI_OPTS}
fi

# uwsgi entrypoint, with fixtures, intended for use in local environment only
if [ "$1" = 'uwsgi_fixtures' ]; then
    echo "[Run] Starting uwsgi with fixtures"

    : ${UWSGI_OPTS="/app/uwsgi/docker.ini"}
    echo "UWSGI_OPTS is ${UWSGI_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_dev_fixtures
    _django_check_deploy

    exec uwsgi --die-on-term --ini ${UWSGI_OPTS}
fi

# runserver entrypoint
if [ "$1" = 'runserver' ]; then
    echo "[Run] Starting runserver"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_dev_fixtures

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
fi

# grdr entrypoint
if [ "$1" = 'grdr' ]; then
    echo "[Run] Starting runserver with GRDR data elements"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_dev_fixtures
    _rdrf_import_grdr

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
fi

# runserver lettuce entrypoint
if [ "$1" = 'runserverlettuce' ]; then
    echo "[Run] Starting runserver"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    _django_collectstatic
    _django_migrate
    _django_iprestrict_permissive_fixtures

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
fi



# runtests entrypoint
if [ "$1" = 'runtests' ]; then
    echo "[Run] Starting tests"
    exec django-admin.py test --noinput -v 3 rdrf
fi

# lettuce entrypoint
if [ "$1" = 'lettuce' ]; then
    echo "[Run] Starting lettuce"
    selenium_defaults
    rm -f /data/*.png
    exec django-admin.py run_lettuce --with-xunit --xunit-file=/data/tests.xml
fi

# selenium entrypoint
if [ "$1" = 'selenium' ]; then
    echo "[Run] Starting selenium"
    selenium_defaults
    exec django-admin.py test --noinput -v 3 /app/rdrf/rdrf/selenium_test/ --pattern=selenium_*.py
fi

echo "[RUN]: Builtin command not provided [tarball|lettuce|selenium|runtests|runserver|uwsgi|uwsgi_fixtures]"
echo "[RUN]: $@"

exec "$@"
