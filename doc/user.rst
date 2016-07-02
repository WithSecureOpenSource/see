User Manual
===========

This section describes how to operate a Platform developed with SEE. The Environment interface and its documentation will be introduced to the reader. It will follow a description of the supported virtualization technologies and how to configure them.

Configuration
-------------

SEE configuration represents the interface the User can employ to describe a Test Case. It includes the chosen Sandbox technology, its specifications and the Hooks which will drive the test with their related options.

SEE requires a configuration for the Sandbox technology, usually referred as Resources configuration, and one for the Hooks. The Resources configuration is provided to a Context Factory callable which is responsible to spawn a new Sandbox. The Hooks configuration instead, will be passed to the Environment class constructor altogether with the Context Factory callable.

The configurations can be passed to the constructors both as a dictionary or as the path to the file in which they are stored, in the latter case the JSON format is the accepted one.

Hooks
+++++

The `hooks` section includes the list of required Hooks for the specific Test Case and their configuration.
For each Hook, the User must provide its Python fully qualified name (PEP-3155). Furthermore, a set of configuration values can be specified either generic for all Hooks or Hook specific.

The example shows a configuration section including two Hooks - Hook1 and Hook2 - which will both receive the `hook_generic` configuration value while only Hook1 will have the `hook_specific` one.

::

  {
      "hooks":
      {
          "configuration":
          {
              "hooks_generic": "Hooks generic configuration value"
          },
          "hooks":
          [
              {
                  "name": "python.fully.qualified.name.Hook1",
                  "configuration":
                  {
                      "hook_specific": "Hook specific configuration value"
                  }
              },
              {
                  "name": "python.fully.qualified.name.Hook2",
                  "configuration": {}
              }
          ]
      }
  }

Resources
+++++++++

SEE `resources` describes the layout of the sandboxes and their capabilities. Their configuration may vary according to the sandboxing technology which has been chosen. SEE includes a minimal support for QEMU/KVM, Virtualbox and Linux Containers but allows Developers to expand it though a simple interface.

The `resources` configuration syntax is virtualization provider specific and its details can be found within the modules implementation under:

::

  see/context/resources/

The resources capabilities and configuration vary according to the sandbox provider chosen for the Test Case.

Linux Container (LXC)
^^^^^^^^^^^^^^^^^^^^^

Linux Container resources are provided by the module contained in:

::

   see/context/resources/lxc.py

The `hypervisor` field is optional and allows the User to define the URL of the hypervisor driver, SEE can control Linux Containers located in remote machines as well. If not provided, the URL will point to the local host.

The `domain` field controls the sandbox instance properties, it must include the path to the Libvirt's specific configuration XML file under the `configuration` field. Please refer to the `libvirt Linux Container <http://libvirt.org/drvlxc.html>`_ page for configuring a LXC domain.

The following tags are dynamically set, if missing, in the `domain` XML configuration:

  - name: set as the Environment's UUID.
  - uuid: set as the Environment's UUID.

Additionally, the User can specify one or more file system mounts to be exposed within the Linux Container. For each entry in the `filesystem` field, a `source_path` must be specified representing the mount location on the host side. In such location, a temporary subfolder, named as the Environment's UUID, will be created avoiding collisions with other containers pointing at the same place. The `target_path` instead, contains the path which will be visible within the container. The mount points will be readable and writable from both the host and the guest sides.

The User can attach a Linux Container to a dynamically provisioned network relieving the User from their creation and management. See the Network section for more information.

The following JSON snippet shows an example of a LXC configuration.

::

  {
      "hypervisor": "lxc:///",
      "domain":
      {
          "configuration": "/etc/myconfig/see/domain.xml",
          "filesystem":
          [
              {
              "source_path": "/srv/containers",
              "target_path": "/"
              },
              {
              "source_path": "/var/log/containers",
              "target_path": "/var/log"
              }
          ]
      },
      "network":
      { "See Network section" }
  }


QEMU/KVM
^^^^^^^^

QEMU resources are provided by the module contained in:

::

   see/resources/qemu.py

The `hypervisor` field is optional and allows the User to define the URL of the hypervisor driver, SEE can control QEMU instances running in remote machines as well. If not provided, the URL will point to qemu:///system.

The `domain` field controls the sandbox instance properties, it must include the path to the Libvirt's specific configuration XML file under the `configuration` field. Please refer to the `libvirt QEMU <http://libvirt.org/drvqemu.html>`_ page for configuring a QEMU/KVM domain.

The following tags are dynamically set, if missing, in the `domain` XML configuration:

  - name: set as the Environment's UUID.
  - uuid: set as the Environment's UUID.

The `disk` field must be provided with the `image` key containing the path to the disk image file intended to be used. Furthermore, the disk image must be contained in a `Libvirt's storage pool <http://libvirt.org/storage.html#StorageBackendDir>`_.

It is a common use case to start the virtual machine from a specific state - for example with the operative system installed and configured - preserving it for different tests. To fulfil this requirement, the original disk image can be cloned into a new one which will be employed to perform the test.

If the `clone` section it's provided, a `storage_pool_path` must be present. A storage pool consists of a folder in which all the disk image files associated to a domain are contained. Within the given path, a new directory will be created with the Environment's UUID as name and it will contain the clone of the original disk image.

The optional `copy_on_write` boolean flag dictates whether the whole disk image will be cloned or only the new files created during the test execution. This allows to save a considerable amount of disk space but the original disk image must be available during all the Environment's lifecycle.

The User can attach a QEMU Virtual Machine to a dynamically provisioned network relieving the User from their creation and management. See the Network section for more information.

The following JSON snippet shows an example of a QEMU configuration.

::

  {
      "hypervisor": "qemu:///system",
      "domain":
      {
          "configuration": "/etc/myconfig/see/domain.xml",
      },
      "disk":
      {
          "image": "/var/mystoragepool/image.qcow2",
          "clone":
          {
              "storage_pool_path": "/var/data/pools",
              "copy_on_write": true
          }
      },
      "network":
      { "See Network section" }
  }


Virtualbox
^^^^^^^^^^

Unfortunately, due to the limited Virtualbox support offered by Libvirt, the amount of customisation is pretty poor. Nevertheless, the Virtualbox default resource provider can be expanded in order to increase its capabilities, please refer to the `The Resources Class` subchapter under the `Developer Manual` section to see how to customise the default resource providers.

Virtualbox resources are provided by the module contained in:

::

  see/resources/vbox.py

The `hypervisor` field is optional and allows the User to define the URL of the hypervisor driver, SEE can control Virtualbox instances running in remote machines as well. If not provided, the URL will point to vbox:///session.

The `domain` field controls the sandbox instance properties, it must include the path to the Libvirt's specific configuration XML file under the `configuration` field. Please refer to the `libvirt Virtualbox <http://libvirt.org/drvvbox.html>`_ page for configuring a Virtualbox domain.

The following tags are dynamically set, if missing, in the `domain` XML configuration:

  - name: set as the Environment's UUID.
  - uuid: set as the Environment's UUID.

The `disk` field must be provided with the `image` key containing the path to the disk image file intended to be used.

The following JSON snippet shows an example of a Virtualbox configuration.

::

  {
      "name": "see.resources.vbox.VBoxResources",
      "hypervisor": "vbox:///session",
      "domain":
      {
          "configuration": "/etc/myconfig/see/domain.xml",
      },
      "disk":
      {
          "image": "/var/mystoragepool/image.vdi",
      }
  }

Network
^^^^^^^

Network resources are provided by the module contained in:

::

  see/resources/network.py

A typical scenario is the execution of a Sandbox connected to a subnetwork. For the simplest use cases, libvirt's default network is enough. Yet there are different situations in which, for example, the User wants to execute multiple sandboxes on the same host ensuring their network isolation.

SEE can provision a subnetwork attaching to it the sandbox and taking care of its allocation and removal. This feature is controlled by the `network` field.

The `network` field specifies the virtual subnetwork in which the container will be placed. As for the `domain`, a `configuration` file must be provided. Please refer to the `libvirt Networking <http://libvirt.org/formatnetwork.html>`_ page for configuring a virtual network.

If provided, the `dynamic_address` will delegate to SEE the generation of a valid IPv4 address, the XML configuration must not contain an `ip` field if so. The User must specify the address and prefix of the network in which to create the subnetwork as well as the subnetwork prefix. SEE will generate a random subnetwork address according to the specifications avoiding collisions with other existing libvirt networks. A DHCP server will be provided within the subnetwork serving the sandbox guest Operating System.

The following JSON snippet shows an example of a network configuration with dynamic address generation.

::

  {
      "configuration": "/etc/myconfig/see/network.xml",
      "dynamic_address":
      {
          "ipv4": "192.168.0.0",
          "prefix": 16,
          "subnet_prefix": 24
      }
  }

In the following example, SEE will generate a subnetwork within the network 192.168.0.0/16. The subnetwork will have the address 192.168.X.0/24 where X is a random number in the range 0-255. The DHCP server will assign addresses to the sandbox in the range 192.168.X.[0-255].
