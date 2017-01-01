.. Sandboxed Execution Environment documentation master file, created by
   sphinx-quickstart on Fri Sep 25 15:07:57 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Sandboxed Execution Environment
===============================

Sandboxed Execution Environment provides a secure framework for test automation of software which behaviour is unknown and must be investigated. Aim of SEE is to empower its users allowing them to quickly build automated test cases in order to keep up with the progressing speed of software evolution.

SEE is very well suited for automating malware analysis, vulnerability discovery and software behavioural analysis in general.

Contents:
=========

.. toctree::
   :maxdepth: 2

   rationale
   setup
   user
   developer
   examples

Tutorial
--------

This tutorial will give an introduction on how to setup an example analysis environment using SEE.

The environment will comprise a Windows 7 Operating System virtualized using QEMU/KVM on a Debian derived distribution (Debian Stretch).

.. toctree::
    :maxdepth: 2

    tutorial_installation.rst
    tutorial_setup.rst
    tutorial_hellosandbox.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
