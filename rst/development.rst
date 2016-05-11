.. _development:

Development Environment
=======================

Setting up your development environment
---------------------------------------
After downloading the source and decompressing:

1. first install docker ( https://www.docker.com/ ) and python tools pip and virtualenv.
2. cd in to the source directory
3. issue the command: ./develop.sh start  ( this will install a tool which creates the application containers and wires them up.)
4. open a web browser at localhost:8000 and login with the (dev only!) admin account (password admin)
5. look at :ref:`How to create a registry <howtocreatearegistry>`

Commands - Using develop.sh
===========================

usage
------------------
Usage ./develop.sh (pythonlint|jslint|start|rpmbuild|rpm_publish|unit_tests|selenium|lettuce|ci_staging)


start
-----
./develop.sh start

This brings up the dev container - login at localhost:8000

Changes to the code are automatically picked up.
Data and logs in ./data/dev

unit tests
----------
./develop.sh unit_tests

selenium tests
--------------
./develop.sh selenium


Commands - Using fig
====================

RDRF can also be run via fig on the command line inside the source directory ( NB fig (http://www.fig.sh/) should be installed)

NB. cd into source folder first for these commands

Starting the development container
----------------------------------
fig up

Running unit tests
------------------
fig -f fig-test.yml up

Running selenium tests
----------------------
fig -f fig-selenium.yml up