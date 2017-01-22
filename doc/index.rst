.. Sandboxed Execution Environment documentation master file, created by
   sphinx-quickstart on Fri Sep 25 15:07:57 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Sandboxed Execution Environment
===============================

Sandboxed Execution Environment provides a secure framework for test automation of software which behaviour is unknown and must be investigated. Aim of SEE is to empower its users allowing them to quickly build automated test cases in order to keep up with the progressing speed of software evolution.

SEE is very well suited for automating malware analysis, vulnerability discovery and software behavioural analysis in general.

Rationale
---------

Analysing the execution of unknown software has become a quite complicated matter. The amount of Operating Systems and libraries to support is growing at an incredible speed. Developing and operating automated behavioural analysis platforms requires several different areas of expertise. The co-operation of such fields is critical for the effectiveness of the end product.

F-Secure developed its first prototype for an automated behavioural analysis platform in 2005. The expertise acquired over the years led to the need for a better approach in building such technologies. Rather than a single and monolithic platform trying to cover all the possible scenarios, a family of specifically tailored ones seemed a more reasonable approach for the analysis of unknown software.

Sandboxed Execution Environment has been built to enable F-Secure malware experts to quickly prototype and develop behavioural analysis engines.

The technology consists of few well known design patterns enclosed in a small framework. With SEE is possible to quickly deploy a Sandbox and attach different plugins to control it. The overall design allows to build highly flexible, robust and relatively safe platforms for test automation.

Tutorial
--------

This tutorial will give an introduction on how to setup an example analysis environment using SEE.

The environment will comprise a Windows 7 Operating System virtualized using QEMU/KVM on a Debian derived distribution (Debian Stretch).

.. toctree::
   :maxdepth: 2

   tutorial_installation.rst
   tutorial_setup.rst
   tutorial_hellosandbox.rst
   tutorial_plugins.rst
   tutorial_injection.rst
   tutorial_hellomalware.rst
   tutorial_conclusions.rst

Documentation
-------------

.. toctree::
   :maxdepth: 2

   setup
   user
   developer

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
