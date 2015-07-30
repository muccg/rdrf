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

To start up the RDRF Backend start Celery::

 # service mongod start


At this stage you should be able to access the RDRF web application by browsing to https://YOURHOST/rdrf/.

The RDRF default installation creates two users *demo* and *admin*, where *demo* is a normal user and *admin* is RDRF administrator.
The password for *demo* is *demo* and for *admin* is *admin*.
