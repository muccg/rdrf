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

    : ${DOCKER_ROUTE:=$(/sbin/ip route|awk '/default/ { print $3 }')}

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

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MONGOSERVER MONGOPORT MEMCACHE DOCKER_ROUTE
    export REPORTDBSERVER REPORTDBPORT REPORTDBUSER REPORTDBPASS
}


trap exit SIGHUP SIGINT SIGTERM
defaults
env | grep -iv PASS | sort
wait_for_services

# prepare a tarball of build
if [ "$1" = 'tarball' ]; then
    echo "[Run] Preparing a tarball of build"

    cd /app
    rm -rf /app/*
    echo $GIT_TAG
    set -x
    git clone --depth=1 --branch=$GIT_TAG git@bitbucket.org:ccgmurdoch/angelman.git .

    # install python deps
    # Note: Environment vars are used to control the bahviour of pip (use local devpi for instance)
    pip install ${PIP_OPTS} --upgrade -r rdrf/runtime-requirements.txt
    pip install -e rdrf
    set +x

    # create release tarball
    DEPS="/env /app/uwsgi /app/docker-entrypoint.sh /app/rdrf"
    cd /data
    exec tar -cpzf angelman-${GIT_TAG}.tar.gz ${DEPS}
fi

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

echo "[RUN]: Builtin command not provided [tarball|lettuce|selenium|runtests|runserver|uwsgi]"
echo "[RUN]: $@"

exec "$@"
