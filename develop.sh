#!/bin/sh
#
# Script for dev, test and ci
#

: ${PROJECT_NAME:='rdrf'}
. ./lib.sh

# break on error
set -e

ACTION="$1"


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
    echo " ./develop.sh (baseimage|buildimage|devimage|releasetarball|prodimage)"
    echo " ./develop.sh (dev|dev_build|django_admin|check_migrations)"
    echo " ./develop.sh (prod|prod_build)"
    echo " ./develop.sh (runtests|dev_aloe|prod_aloe|reexport_test_zips)"
    echo " ./develop.sh (start_test_stack|start_seleniumhub)"
    echo " ./develop.sh (pythonlint|jslint)"
    echo " ./develop.sh (ci_docker_login)"
    echo ""
    echo "Example, start dev with no proxy and rebuild everything:"
    echo "SET_PIP_PROXY=0 SET_HTTP_PROXY=0 ./develop.sh dev_build"
    echo ""
    echo "Example, run test suite against a single feature:"
    echo "./develop.sh dev_aloe rdrf/features/landing.feature"
    exit 1
}


# lint using flake8
python_lint() {
    info "python lint"
    docker-compose -f docker-compose-build.yml run --rm lint flake8 rdrf --exclude=migrations --ignore=E501 --count
    success "python lint"
}


# lint js, assumes closure compiler
js_lint() {
    info "js lint"
    JSFILES=`ls rdrf/rdrf/static/js/*.js | grep -v "\.min\."`
    EXCLUDES='-x rdrf/rdrf/static/js/gallery.js,rdrf/rdrf/static/js/ie_select.js,rdrf/rdrf/static/js/jquery.bootgrid.js,rdrf/rdrf/static/js/nv.d3.js'
    for JS in $JSFILES
    do
        docker-compose -f docker-compose-build.yml run lint gjslint ${EXCLUDES} --disable 0131 --max_line_length 100 --nojsdoc $JS
    done
    success "js lint"
}


reexport_test_zips() {
  ZIPFILES=rdrf/rdrf/features/exported_data/*.zip
  for f in $ZIPFILES
  do
      code=$(basename --suffix=.zip $f)
      reexport_test_zip /app/$f $code
  done
}

reexport_test_zip() {
    info 'reexport test zips'
    _start_test_stack --force-recreate -d

    set -x
    set +e
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-teststack.yml run --rm runservertest /app/docker-entrypoint.sh /app/scripts/reexport_zip.sh "$@"
    local rval=$?
    set -e
    set +x

    _stop_test_stack
    return $rval
}


echo ''
info "$0 $@"
docker_options
git_tag

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
dev_build)
    create_base_image
    create_build_image
    create_dev_image
    ;;
django-admin)
    shift
    django_admin $@
    ;;
check_migrations)
    check_migrations
    ;;
releasetarball)
    create_release_tarball
    ;;
prod)
    start_prod
    ;;
prod_build)
    create_base_image
    create_build_image
    create_release_tarball
    create_prod_image
    ;;
baseimage)
    create_base_image
    ;;
buildimage)
    create_build_image
    ;;
prodimage)
    create_prod_image
    ;;
devimage)
    create_dev_image
    ;;
publish_docker_image)
    publish_docker_image
    ;;
runtests)
    create_base_image
    create_build_image
    create_dev_image
    run_unit_tests
    ;;
start_test_stack)
    start_test_stack
    ;;
start_seleniumhub)
    start_seleniumhub
    ;;
docker_warm_cache)
    docker_warm_cache
    ;;
ci_docker_login)
    ci_docker_login
    ;;
dev_aloe)
    shift
    dev_aloe $@
    ;;
aloe)
    shift
    dev_aloe $@
    ;;
reexport_test_zips)
    reexport_test_zips
    ;;
prod_aloe)
    shift
    prod_aloe $@
    ;;
*)
    usage
    ;;
esac
