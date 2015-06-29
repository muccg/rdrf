.. rdrf documentation master file, created by
   sphinx-quickstart on Tue Jan 14 10:39:07 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

About the Rare Disease Registry Framework
=========================================

The Rare Disease Registry Framework (RDRF) is an open source tool for the creation of web-based Patient 
Registries, which delivers the features that you and/or your organisation currently require. The RDRF is
flexible, and your Registry can be customised and enhanced to evolve as your needs change. 
The RDRF empowers Patient Organisations, Clinicians and Researchers to create and manage their 
own Patient Registries, without the need for software development. 

The RDRF is unique in that data entry forms and questionnaires are based on reusable data element definitions 
(called :ref:`des`), which can be created and/or loaded into the system at runtime. 
This means that registries can be created and modified without changes to the source code. The RDRF has 
been developed at the `Centre for Comparative Genomics <http://ccg.murdoch.edu.au>`_, Murdoch University, Western Australia 
in partnership with the Office of Population Health Genomics, Department of Health 
Western Australia.


Do you need a patient registry for your department, clinic or community?
========================================================================

The RDRF enables the rapid creation of Registries without the need for software development through 
the following key features:
  - Dynamic creation of :ref:`registries` (comprised of :ref:` forms <registriesforms>`, :ref:`sections <registriessections>', and :ref:`des`,) at *runtime*
  - Reusable Components (:ref:`des`) allows CDEs to be used in multiple registries
  - Patients can be defined once, and belong to several registries
  - Multiple levels of access are supported (e.g. patient, clinician, genetic, and curator roles)

The RDRF can be used to create different types of registries, such as a Contact Registry or a more complex registry with the ability to restrict 
Forms to certain groups of users. Please see this `video <https://www.youtube.com/watch?v=hsqpvLIbmNA>`_ for a quick demonstration.

Are you ready to create your own Patient Registry?
==================================================

A `Demo Site <https://rdrf.ccgapps.com.au/demo/>`_ is available for you to try out online. Different levels of access are available, including admin, 
data curator, genetic staff and clinical staff:
  - admin username and password: admin
  - data curator username and password: curator
  - genetic staff username and password: genetic
  - clinical staff username and password: clinical

Screencasts are available to talk you through the creation of a Registry:
  - `Training videos (with audio) to create a Registry as an admin user <https://www.youtube.com/playlist?list=PL_54ZaRad-lT-3emdPkc75uBt5aiX1Hn1>`_
  - `Training videos (with text) to create a Registry as an admin user <https://www.youtube.com/playlist?list=PL_54ZaRad-lSWLUNTqrIpfBuUfHzidbfu>`_
  - `Training videos to add a Patient as a curator user <https://www.youtube.com/watch?v=O1se5ATJ9jU&list=PL_54ZaRad-lS5cImArcSaAZhnwISPrIOz>`_

If you prefer to read:
  - Here's some text explaining how to create a :ref:`registry in 10 minutes <howtocreatearegistry>`


Documentation Content List:
===========================


.. toctree::
   :maxdepth: 3

   workflow
   designmode
   gui
   registries
   cdes
   datatypes
   howtocreatearegistry
   permittedvaluegroups
   permittedvalue
   import
   questionnaires
   interfacing
   about
   development


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

