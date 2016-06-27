.. _development:

Development Environment
=======================

Setting up your development environment
---------------------------------------

Prerequisites:

1. Docker ( https://www.docker.com/ )
2. docker-compose ( https://docs.docker.com/compose/ )
3. Python 2.7

After downloading the source and decompressing:

1. cd in to the source directory
2. issue the command: ./develop.sh dev_build
3. issue the command: ./develop.sh dev
4. open a web browser at localhost:8000 and login with the (dev only!) admin account (password admin)
5. look at :ref:`How to create a registry <howtocreatearegistry>`

Commands - Using develop.sh
===========================

develop.sh is primarily a thin wrapper calling docker-compose. By all means use docker-compose directly if that is your preference.

usage
-----
Usage::

# ./develop.sh (baseimage|buildimage|devimage|releasetarball|prodimage)
# ./develop.sh (dev|dev_build)
# ./develop.sh (start_prod|prod_build)
# ./develop.sh (runtests|lettuce|selenium)
# ./develop.sh (start_test_stack|start_seleniumhub|start_seleniumtests|start_prodseleniumtests)
# ./develop.sh (pythonlint|jslint)
# ./develop.sh (ci_dockerbuild)
# ./develop.sh (ci_docker_staging|docker_staging_lettuce)

dev stack
---------
To start up the dev stack::

# ./develop.sh dev

Login at localhost:8000


Changes to the code are automatically picked up.
Data and logs in ./data/dev

unit tests
----------
To run unit tests::

# ./develop.sh runtests

selenium tests
--------------
To run selenium tests::

# ./develop.sh selenium
