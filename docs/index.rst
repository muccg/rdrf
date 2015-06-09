.. rdrf documentation master file, created by
   sphinx-quickstart on Tue Jan 14 10:39:07 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

About the Rare Disease Registry Framework
=========================================

The Rare Disease Registry Framework (RDRF) is an open source tool for the creation of web-based patient 
registries, which delivers the features needed to support improved health outcomes for patients and patient 
organisations. The RDRF empowers Patient Organisations, Clinicians and Researchers to create and manage their 
own Patient Registries, without the need for software development. 

The RDRF is unique in that data entry forms and questionnaires are based on reusable data element definitions 
(called *Common Data Elements* ( :ref:`cdes` ), which can be created and/or loaded into the system at runtime. 
This means that registries can be created and modified without changes to the source code#. The RDRF has 
been developed at the `Centre of Comparative Genomics (`_<http://ccg.murdoch.edu.au>`_), Murdoch University, 
Western Australia in partnership with the Office of Population Health Genomics, Department of Health 
Western Australia.


Do you need a patient registry for your department, clinic or community?
========================================================================

The RDRF enables the rapid creation of Registries without the need for software development through 
the following key features:
  - Dynamic creation of :ref:`registries` (comprised of :ref:`forms` , :ref:`sections' , and :ref:`cdes` ) at *runtime*
  - Reusable Components ( :ref:`cdes` ) allows CDEs to be used in multiple registries
  - Patients can be defined once, and belong to several registries
  - Multiple levels of access are supported (e.g. patient, clinician, genetic, and curator roles).


Welcome to rdrf's documentation!!!
================================

Contents:

.. toctree::
   :maxdepth: 3

   workflow
   designmode
   gui
   registries
   howtocreatearegistry
   forms
   sections
   cdes
   permittedvaluegroups
   permittedvalue
   datatypes
   export
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

