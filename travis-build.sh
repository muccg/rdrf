#!/bin/bash

set -e 

#
# Development build and tests
#

# ccg-composer runs as this UID, and needs to be able to
# create output directories within it
mkdir -p data/
sudo chown 1000:1000 data/

./develop.sh build base
./develop.sh build builder
./develop.sh build node
./develop.sh build dev
./develop.sh check-migrations
./develop.sh run-unittests
./develop.sh aloe teststack
./develop.sh run build lint
./develop.sh run "" node lint
