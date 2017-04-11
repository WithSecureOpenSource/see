Installation
============

Please refer to the `installation documentation <http://pythonhosted.org/python-see/setup.html>`_ if problems are encountered.

Requirements
------------

The following base Debian packages are required.

  - python3
  - python3-pip

The following Debian packages provide the core virtualization technologies.

  - qemu
  - qemu-tools
  - dnsmasq
  - virt-viewer
  - virtinst
  - python3-libvirt

These Debian packages are required in the Tutorial's last chapters.

  - tshark
  - volatility
  - virt-manager
  - python3-guestfs
  - python3-requests

This Python package is required in the Tutorial's last chapters.

  - `vminspect <https://github.com/noxdafox/vminspect>`_

Set up
------

SEE can be installed using pip.

::

  # pip3 install python-see

For correct operation, the user which will run the analysis platform will need to be part of the following groups.

  - kvm
  - libvirt
  - libvirt-qemu

The following command allows to add a user to a group.

::

  # adduser <username> <group>

Make sure hardware acceleration is supported.

To verify that KVM is available it is enough to run:

::

  # modprobe kvm
  # modprobe kvm_intel

for Intel processors or:

::

  # modprobe kvm
  # modprobe kvm_amd

for AMD ones.
