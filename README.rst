Sandboxed Execution Environment
===============================

Introduction
------------

Sandboxed Execution Environment (SEE) is a framework for building test automation in secured Environments.

The Sandboxes, provided via libvirt, are customizable allowing high degree of flexibility. Different type of Hypervisors (Qemu, VirtualBox, LXC) can be employed to run the Test Environments.

Plugins can be added to a Test Environment which provides an Event mechanism synchronisation for their interaction. Users can enable and configure the plugins through a JSON configuration file.

Audience
--------

SEE is for automating tests against unknown, dangerous or unstable software tracking its activity during the execution.

SEE is well suited for building modular test platforms or managing executable code with a good degree of isolation.

SEE allows to write sandboxed tests both for quick prototyping and for running on production environment.

Installation
------------

SEE is available as Python package on the Python Package Index (PyPI).

It's user's responsibility to install and setup the hypervisors intended to be controlled with SEE.

Please refer to the documentation to see how to setup and configure each hypervisor.

Supported hypervisors
---------------------

SEE is build on top of libvirt's APIs, therefore all hypervisors supported by libvirt can be controlled through SEE.

SEE comes with a basic support for QEMU, VirtualBox and LXC, to add more hypervisor or customize the basic ones see the code contained in see/context.

Principles
----------

SEE is an event-driven, plugin-based sandbox provider for synchronous and asynchronous test flow control.

::


                                                                      +----------+
                                                                      |          |
                                                              +-------| SEE Hook |
                                                              |       |          |
                                                              |       +----------+
                  +-----------------+       +---------+       |       +----------+
                  |                 |       |         |       |       |          |
    User -------> | SEE Environment |-------| Sandbox |-------+-------| SEE Hook |
                  |                 |       |         |       |       |          |
                  +-----------------+       +---------+       |       +----------+
                                                              |       +----------+
                                                              |       |          |
                                                              +-------| SEE Hook |
                                                                      |          |
                                                                      +----------+

A SEE Environment encapsulates all the required resources acting as a handler for the User. The Sandbox is controlled by the Hooks which act as plugins, Hooks communicate and co-ordinate themselves through Events.

Each Hook has direct access to the Sandbox which exposes a simple API for it's control and libvirt's APIs for more fine grained control.

Links
-----

Project page.

https://pypi.python.org/pypi/python-see

Project documentation.

https://pythonhosted.org/python-see

Libvirt project page.

https://libvirt.org

Presentation on PyCon Finland 2015.

https://www.youtube.com/watch?v=k185OMivqbQ
