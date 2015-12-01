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
        dockerwait $REPORTDBSERVER $REPORTDBPORT
    fi
}


function defaults {
    : ${ENV_PATH:="/env/bin"}

    : ${DBSERVER:="db"}
    : ${DBPORT:="5432"}

    : ${REPORTDBSERVER:="reporting"}
    : ${REPORTDBPORT:="5432"}
    : ${REPORTDBUSER="reporting"}
    : ${REPORTDBNAME="${DBUSER}"}
    : ${REPORTDBPASS="${DBUSER}"}

    : ${RUNSERVER="web"}
    : ${RUNSERVERPORT="8000"}
    : ${CACHESERVER="cache"}
    : ${CACHEPORT="11211"}
    : ${MONGOSERVER="mongo"}
    : ${MONGOPORT="27017"}

    : ${DBUSER="webapp"}
    : ${DBNAME="${DBUSER}"}
    : ${DBPASS="${DBUSER}"}

    . ${ENV_PATH}/activate

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MONGOSERVER MONGOPORT
    export REPORTDBSERVER REPORTDBPORT REPORTDBUSER REPORTDBPASS
}


function django_defaults {
    : ${DEPLOYMENT="dev"}
    : ${PRODUCTION=0}
    : ${DEBUG=1}
    : ${MEMCACHE="${CACHESERVER}:${CACHEPORT}"}
    : ${WRITABLE_DIRECTORY="/data/scratch"}
    : ${STATIC_ROOT="/data/static"}
    : ${MEDIA_ROOT="/data/static/media"}
    : ${LOG_DIRECTORY="/data/log"}
    : ${DJANGO_SETTINGS_MODULE="django.settings"}
    : ${MONGO_DB_PREFIX="dev_"}

    echo "DEPLOYMENT is ${DEPLOYMENT}"
    echo "PRODUCTION is ${PRODUCTION}"
    echo "DEBUG is ${DEBUG}"
    echo "MEMCACHE is ${MEMCACHE}"
    echo "WRITABLE_DIRECTORY is ${WRITABLE_DIRECTORY}"
    echo "STATIC_ROOT is ${STATIC_ROOT}"
    echo "MEDIA_ROOT is ${MEDIA_ROOT}"
    echo "LOG_DIRECTORY is ${LOG_DIRECTORY}"
    echo "DJANGO_SETTINGS_MODULE is ${DJANGO_SETTINGS_MODULE}"
    echo "MONGO_DB_PREFIX is ${MONGO_DB_PREFIX}"
    
    export DEPLOYMENT PRODUCTION DEBUG DBSERVER MEMCACHE WRITABLE_DIRECTORY STATIC_ROOT MEDIA_ROOT LOG_DIRECTORY DJANGO_SETTINGS_MODULE MONGO_DB_PREFIX
}

echo "HOME is ${HOME}"
echo "WHOAMI is `whoami`"

defaults
django_defaults
wait_for_services

# uwsgi entrypoint
if [ "$1" = 'uwsgi' ]; then
    echo "[Run] Starting uwsgi"

    : ${UWSGI_OPTS="/app/uwsgi/docker.ini"}
    echo "UWSGI_OPTS is ${UWSGI_OPTS}"

    django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-collectstatic.log
    django-admin.py migrate  --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-migrate.log
    django-admin.py update_permissions --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/uwsgi-permissions.log

    exec uwsgi --die-on-term --ini ${UWSGI_OPTS}
fi

# runserver entrypoint
if [ "$1" = 'runserver' ]; then
    echo "[Run] Starting runserver"

    : ${RUNSERVER_OPTS="runserver_plus 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}"}
    echo "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"

    echo "running collectstatic"
    django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/runserver-collectstatic.log

    echo "running migrate ..."
    django-admin.py migrate  --settings=${DJANGO_SETTINGS_MODULE}  2>&1 | tee /data/runserver-migrate.log

    echo "updating permissions"
    django-admin.py update_permissions  --settings=${DJANGO_SETTINGS_MODULE} 2>&1 | tee /data/runserver-permissions.log

    echo "loading rdrf fixture"
    django-admin.py load_fixture --settings=${DJANGO_SETTINGS_MODULE} --file=rdrf.json

    echo "loading users fixture"
    django-admin.py load_fixture --settings=${DJANGO_SETTINGS_MODULE} --file=users.json

    echo "running runserver ..."
    exec django-admin.py ${RUNSERVER_OPTS}
fi

# runtests entrypoint
if [ "$1" = 'runtests' ]; then
    echo "[Run] Starting tests"
    exec django-admin.py test rdrf
fi

# lettuce entrypoint
if [ "$1" = 'lettuce' ]; then
    echo "[Run] Starting lettuce"
    exec django-admin.py run_lettuce --with-xunit --xunit-file=/data/tests.xml
fi

# selenium entrypoint
if [ "$1" = 'selenium' ]; then
    echo "[Run] Starting selenium"
    exec django-admin.py test /app/rdrf/rdrf/selenium_test/ --pattern=selenium_*.py
fi

echo "[RUN]: Builtin command not provided [lettuce|selenium|runtests|runserver|uwsgi]"
echo "[RUN]: $@"

exec "$@"
