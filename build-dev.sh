#!/bin/bash

set -e 

./develop.sh build base
./develop.sh build builder
./develop.sh build node
./develop.sh build dev
./develop.sh check-migrations


