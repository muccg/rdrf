#!/bin/bash

set -e 

#
# Development build and tests
#

# ccg-composer runs as this UID, and needs to be able to
# create output directories within it
mkdir -p data/
sudo chown 1000:1000 data/

echo LINTING
./develop.sh  run build lint --ignore W503,E501,C901 ./rdrf
echo BUILDING BASE
./develop.sh build base
echo BUILDING BUILDER
./develop.sh build builder
echo BUILDING NODE
./develop.sh build node
echo BUILDING DEV
./develop.sh build dev
echo CHECKING MIGRATIONS
./develop.sh check-migrations
echo RUNNING UNIT TESTS
./develop.sh run-unittests
echo RUNNING BEHAVIOURAL TESTS
./develop.sh aloe teststack
echo RUNNING REACT TESTS
./develop.sh run "" node test
echo RUNNING REACT LINT
./develop.sh run "" node lint
