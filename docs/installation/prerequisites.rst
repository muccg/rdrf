.. highlight:: console

.. _prerequisites:

RPM Prerequisites
=================

.. _extra-repos:

Extra CentOS repositories
-------------------------

The EPEL, IUS and CCG rpm repositories are needed to install packages that are not in the CentOS base repositories.

The way to add the EPEL and IUS repositories, depends on the version of CentOS you're having. The following example
is for CentOS 6.6, for other versions of CentOS please follow the instructions at `IUS Repos <https://iuscommunity.org/pages/Repos.html>`_::

 # yum install https://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
 # yum install https://dl.iuscommunity.org/pub/ius/stable/CentOS/6/x86_64/ius-release-1.0-14.ius.centos6.noarch.rpm
 # yum install http://yum.postgresql.org/9.4/redhat/rhel-6-x86_64/pgdg-redhat94-9.4-1.noarch.rpm

To add the CCG repository::

 # yum install http://repo.ccgapps.com.au/repo/ccg/centos/6/os/noarch/CentOS/RPMS/ccg-release-6-2.noarch.rpm

.. _mongodb

MongoDB
--------

RDRF uses MongoDB to store phenotype data. A simple MongoDB installation for evaluating RDRF can be achieved by installing the RPM::

 # yum install mongodb-server

Start the MongoDB service with::

 # service mongod start

