RDRF
====

About
-----

The Rare Disease Registry Framework (RDRF) is an open source tool for the creation of web-based patient registries. What makes it unique is that data entry forms and questionnaires are based on reusable data element definitions (called "Common Data Elements" ) which can be created and/or loaded into the system at runtime. This means that registries can be created and modified without changes to the source code. RDRF has been developed at the `Centre for Comparative Genomics <http://ccg.murdoch.edu.au>`_, Murdoch University, Western Australia in partnership with the `Office of Population Health Genomics <http://www.genomics.health.wa.gov.au>`_, Department of Health Western Australia.


Contact
-------

Hosted on Bitbucket:
 
https://bitbucket.org/ccgmurdoch/rdrf/

Demo Site:

https://rdrf.ccgapps.com.au/demo/

Email:

rdrf@ccg.murdoch.edu.au

Documentation:

http://rare-disease-registry-framework.readthedocs.org/en/latest/


Publications
------------

Matthew I Bellgard, Lee Render, Maciej Radochonski and Adam Hunter, Second generation registry framework, Source Code Biol Med. 2014 Jun 20;9:14.

Matthew Bellgard, Christophe Beroud, Kay Parkinson, Tess Harris, Segolene Ayme, Gareth Baynam, Tarun Weeramanthri, Hugh Dawkins and Adam Hunter, Dispelling myths about rare disease registry system development. Source Code for Biology and Medicine, 2013. 8(1): p. 21.

Rodrigues M, Hammond-Tooke G, Kidd A, Love D, Patel R, Dawkins H, Bellgard M, Roxburgh R, The New Zealand Neuromuscular Disease Registry. J Clin Neurosci, 2012. 19(12): p. 1749-50.

Bellgard MI, Macgregor A, Janon F, Harvey A, O'leary P, Hunter A and Dawkins H, A modular approach to disease registry design: successful adoption of an internet-based rare disease registry. Hum Mutat 33: E2356-2366.


For developers
--------------

We do our development using Docker_ containers.
You will have to set up Docker on your development machine.

Other development dependencies are Python 2 and virtualenv_.

All the development tasks can be done by using the ``develop.sh`` shell script in this directory.
Please run it without any arguments for help on its usage.

A typical usage is::

    ./develop.sh dev_build
    ./develop.sh dev

This will start up all the docker containers needed for dev. 
You can access the RDRF application on http://localhost:8000
(replace localhost with ``$ boot2docker ip`` if using boot2docker) after this.
You can login with one of the default users *admin/admin*.

Note: Our docker containers are coordinated using docker-compose_ which will be installed into a virtualenv environment automatically by the ``./develop.sh`` script for you.

.. _Docker: https://www.docker.com/
.. _docker-compose: https://docs.docker.com/compose/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _devdocs: https://rare-disease-registry-framework.readthedocs.io/en/latest/development.html

Contributing
------------

1. Fork ``next_release`` branch
2. Make changes on a feature branch
3. Submit pull request

