Chiminey
========

.. image:: https://travis-ci.org/chiminey/chiminey.svg?branch=master
   :target: https://travis-ci.org/chiminey/chiminey

Connecting Scientists to HPC, Cloud and Big Data.

Introduction
============

The Chiminey system is a cloud-based computing platform that enables scientists to perform complex computation on cloud-based and traditional high performance computing (HPC) facilities, and  to handle failure during the execution of their application.
This system gives special importance to resource access and management abstraction. Scientists are not expected to have a technical understanding of cloud-computing, HPC, or, big data  fault tolerance in order to leverage the benefits provided by the Chiminey
platform.

Chiminey provides

* Definition, execution and monitoring of high-performance, big data, and cloud computing applications.

* A user interface that focusses  both on the  domain-specific parts of a task for scientists and  a framework that allows IT research engineers
to build computation tasks.

* Automatic generation of  parameter sweeps over variables that can be scheduled on HPC clusters or across cloud IaaS nodes.

* Ability to wrap arbitrary legacy code applications (e.g. fortran), with a minimum of extra work.

* Advanced fault tolerance framework. A smart connector at most recovers a failed execution, at least prevents the failed execution from causing a failure in the entire system:

* Connectors for data transfer to and from remote data sources and remote execution platforms for both unix and cloud computation resources.

* Provides framework for metadata extraction and publishing to the MyTardis data curation system

* Provides APIs for both job submission and monitoring but also redefinition of alternative user interfaces.

The Bioscience Data Platform
----------------------------

Chiminey is a key product of the `Bioscience Data Platform: Tardis in the Cloud project <http://bioscience-data-platform.tumblr.com/>`_, which is a project between Monash University and RMIT University, Victoria Australia funded by NeCTAR.  This project focuses on bringing existing computational systems together in a way that allows scientists to seamlessly work with data from capture through to publication.

Documentation
=============

A Getting Started tutorial is available at `http://chiminey.readthedocs.org/ <http://chiminey.readthedocs.org/>`_, which walks through installation and running simple and then more complicated examples.

 .. An installation manual is available at https://github.com/chiminey/docker-chiminey.

 .. The user manual is available at [readthedocs] (http://chiminey.readthedocs.org/en/latest/enduser_manual.html) .

License
=======

This code is copyright Monash University and RMIT University 2014, and is distributed under the New BSD License

Acknowledgements
================

The BDP project is funded by the NeCTAR, the National eResearch Collaboration Tools and Resources.  NeCTAR is an Australian Government project to build new infrastructure specifically for the needs of Australian researchers.


