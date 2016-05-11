.. highlight:: console

.. _laststeps:

Last steps
==========

At this stage we should have everything installed, the database, caching and sessions configured.

As a last step before starting the applications you should go through all the variables in ``/etc/rdrf/rdrf.conf`` and make sure everything is set to sensible values. See :ref:``settings``.

Restart apache
--------------

To start up the RDRF web application restart Apache::

 # service httpd restart

Start MongoDB
-------------

To start up the MongoDB::

 # service mongod start



Load fixtures
-------------

Create initial users and sample data elements (both files must be loaded in order)::

  # django-admin.py  load_fixture --file=rdrf.json
  # django-admin.py   load_fixture --file=users.json


The following users/password are created:
 * curator/curator
 * genetic/genetic
 * fhcurator/fhcurator
 * clinical/clinical
 * admin/admin

The sample registries are purely for demonstration purposes


NB. After designing a registry ( along with its working groups) - users will need to be assigned to a working and registry
before they will be able to see any data - this is accomplished by logging in as an admin and editing the given user.


At this stage you should be able to access the RDRF web application by browsing to https://YOURHOST/rdrf/.


