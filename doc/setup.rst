Set Up
======

Dependencies
------------

Required:
  - python
  - libvirt

Recommended:
  - qemu-kvm: KVM - Kernel-based virtual machine is a full virtualization solution for Linux.
  - qemu-utils: QEMU utils package includes several useful utilities for handling virtual disk images.
  - virtualbox: Virtualbox is a full-feature virtualization solution.
  - dnsmasq: Dnsmasq is a lightweight DHCP server. It is required by `libvirt` networking stack.


Installation
------------

Be sure to have libvirt's development package installed.

In the root of the project run:

::

  python setup.py install

SEE is available as Python package but it's installation does not bring all the supported hypervisors.

SEE allows to control several different virtualization technologies (QEMU/KVM, Virtualbox, LXC), according to the chosen ones the set up may vary noticeably.
For specific instructions on how to install and set up a given hypervisor, please refer to `libvirt`'s reference documentation.

http://libvirt.org/docs.html

Hardware acceleration for virtualization
----------------------------------------

KVM
+++

To take advantages from hardware acceleration through KVM verify that the processor has VT (Intel) or SVM (AMD) capabilities and that they're enabled in the BIOS configuration.

To verify that KVM is available it is enough to run:

::

  # modporbe kvm_intel

for Intel processors or:

::

  # modporbe kvm_amd

for AMD ones.

If the kernel is able to load the modules then KVM is fully available.

Virtualbox
++++++++++

To use Virtualbox ensure that its driver - `vboxdrv` - is properly loaded in the kernel.
If not, just load it as follows:

::

  # modprobe vboxdrv

Linux Containers (LXC)
++++++++++++++++++++++

Linux Containers require specific Control Groups to be enabled in order to operate:

  - cpuacct
  - memory
  - devices

Additional recommended cgroups:

  - cpu
  - blkio
  - freezer

To enable the required cgroups the User can rely on its init system.
More details at:

http://libvirt.org/cgroups.html

Libvirt networking support
--------------------------

In order to activate the `libvirt` default network interface run the following command.

::

  $ virsh net-start default

To ensure the default network interface to be active after a reboot, enable its autostart property.

::

  $ virsh net-autostart default

Libvirt disk management
-----------------------

`Libvirt` manages the disk image files within storage pools. The storage pools are directories where `libvirt` looks up in order to find the correct disk image.

To create a storage pool, provide an XML file as the one in the example.

::

      <pool type="dir">
        <name>storage_pool_name</name>
        <target>
          <path>/var/lib/virt/images</path>
        </target>
      </pool>

Then load the pool within `libvirt` with the command.

::

  $ virsh pool-create path_to_pool_file.xml

Start the newly created pool.

::

  $ virsh pool-start storage_pool_name

Set the pool to be started at the machine startup.

::

  $ virsh pool-autostart storage_pool_name

Finally, after each new disk image is moved into the pool directory, remember to refresh its list of storage volumes.

::

  $ virsh pool-refresh storage_pool_name

More details about storage pools at:

http://libvirt.org/formatstorage.html

Permissions
-----------

To allow all SEE features to work properly some permission settings must be changed.

Users and groups
++++++++++++++++

Add the SEE user to the libvirt group:

::

  # adduser <username> libvirt

Disk Images Permissions
+++++++++++++++++++++++

All disk images need read and write permissions to be set.

::

  # chmod 644 <disk_image_path>
