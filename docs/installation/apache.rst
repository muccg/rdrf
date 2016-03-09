.. highlight:: console

RPM Installation of the RDRF web application under Apache
=========================================================

The IUS repository provides a ``httpd24u`` package that unfortunately conflicts with ``httpd``.
Therefore if you try to install ``rdrf`` and you don't have one of the ``httpd`` packages already installed you will get a conflict error.
The recommended way (`in the email announcing httpd24u <https://lists.launchpad.net/ius-community/msg01277.html>`_)
to get around this problem is to install the httpd package first and only after that install rdrf::

 # yum install httpd mod_ssl
 # yum install rdrf

This will add an Apache conf file to ``/etc/httpd/conf.d`` called ``rdrf.ccg``. Please feel free to read through it and edit if required.
When you are happy with the contents create a symbolic link for Apache to pick this config up automatically::

 # pushd /etc/httpd/conf.d && ln -s rdrf.ccg rdrf.conf && popd

