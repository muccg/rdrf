#!/bin/bash

set -e 

#
# Development build: lint
#
# Run this last to avoid this blocking push to Docker hub
mkdir -p data/
sudo chown 1000:1000 data/

./develop.sh run build lint
./develop.sh run "" node lint
