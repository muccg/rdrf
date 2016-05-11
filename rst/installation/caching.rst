.. index::
    single: django
    single: caching

.. _caching:

Caching and Sessions
====================

By default RDRF uses database caching and file-based sessions but we recommend using memcached for both.

Changing both caching and session to memcached is therefore easy. Assuming you already have one or more memcached servers ready to go, all you need to do is open ``/etc/rdrf/rdrf.conf`` in your editor and set the ``memcache`` variable to a space-separated list of memcache servers.

This will make RDRF switch to memcached for both caching and sessions.

See:
  * :ref:`settings`
  * `Django caching <https://docs.djangoproject.com/en/dev/topics/cache/>`_
  * `Django sessions <https://docs.djangoproject.com/en/dev/topics/http/sessions/>`_

