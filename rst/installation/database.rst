.. highlight:: console

.. _database-setup:

Database Setup
==============

We assume that you have a database server (preferably Postgres) installed, that is accessible from the server you're performing the RDRF installation on.

Create the RDRF database
------------------------

Please create a database (ex. ``rdrf_prod``) that will be used by the RDRF application.
We recommend creating a user called ``rdrfapp`` with no special privileges that will be the owner of the database.

Configure RDRF to use RDRF database
-----------------------------------

To change the database that RDRF points at you will need to alter the RDRF settings file.
Open up ``/etc/rdrf/rdrf.conf`` in your editor and make sure the variables in the *database options* section (``dbserver``, ``dbname``, ``dbuser`` etc.) are set correctly.

For more details see :ref:`settings`.

Initialise the RDRF database
----------------------------

The RDRF codebase employs `South <http://south.aeracode.org/>`_ to manage schema and data migrations.
To initialise the database::

 # rdrf syncdb --noinput
 # rdrf migrate

These will create the schema, insert setup data, and create initial users.
