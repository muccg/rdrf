#!/bin/sh
cmd=$1

if [ "x$cmd" = "x" ]; then
    # mimic what travis does
    ./develop.sh  run build lint --ignore W503,E501,C901,E203  ./rdrf
elif [ $cmd = "--all" ]; then
    ./develop.sh  run build lint  ./rdrf
fi
