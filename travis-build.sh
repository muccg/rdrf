#!/bin/bash

set -e 

#
# Development build and tests
#

# ccg-composer runs as this UID, and needs to be able to
# create output directories within it
mkdir -p data/
sudo chown 1000:1000 data/


# turn off lint for now - we need to
# to ignore W503 with lint but the muccg/linter
# can't seem to ignore it
# so we should use the alpine flake8 image
#./develop.sh run build lint
./develop.sh build base
./develop.sh build builder
./develop.sh build node
./develop.sh build dev
./develop.sh check-migrations
./develop.sh run-unittests
./develop.sh aloe teststack
./develop.sh run "" node test
./develop.sh run "" node lint
