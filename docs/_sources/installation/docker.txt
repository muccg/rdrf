.. highlight:: console

.. _docker:

Running installation with Docker
======================================

Docker containers wrap up a piece of software in a complete filesystem that contains everything it needs to run: code, runtime, system tools, system libraries – anything you can install on a server. This guarantees that it will always run the same, regardless of the environment it is running in.

For more information please visit the site https://www.docker.com.

Local deployment
----------------

Checkout the source code from the GitHub repository https://github.com/muccg/rdrf.

For stable and up-to-date code please use ``master`` branch::

 # git clone https://github.com/muccg/rdrf.git

Enter the top directory of the source code:: 

 # cd rdrf

To build all the necessary images run::
 
 # ./develop.sh dev_build

After successful build run::

 # docker-compose up

The application is available from::

# http://localhost:8000
# https://localhost:8443/app

or::

# http://<host_ip>:8000
# https://<host_ip>:8443/app
