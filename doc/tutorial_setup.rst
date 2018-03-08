Environment setup
=================

Preparing the Guest Image
-------------------------

In order to perform our tests, we need to provide a copy of a Windows Operating System to be executed within a Virtual Machine.

Microsoft made available for downloading `ready-made virtual machine disk images <https://developer.microsoft.com/en-us/microsoft-edge/tools/vms/>`_ containing Windows 7.

These images are for testing purposes only and they do not allow samples analysis at scale. Yet they are a good starting point for our analysis environment.

Unfortunately, there are no QCOW2 copies available. Even though QEMU allows to execute other disk formats, it is highly recommended to convert the downloaded disk image in QCOW2 format. The VMWare platform is the one used in the Tutorial.

If the downloaded ZIP archive contains an OVA file, the following command will successfully unpack it.

::

  $ tar -xvf "IE8 - Win7.ova"
  IE8 - Win7.ovf
  IE8 - Win7-disk1.vmdk

The OVF file can be automatically converted and imported using virt-convert tool.

::

  $ mkdir /home/username/images
  $ virt-convert --disk-format qcow2 --destination /home/username/images --connect qemu:///system "./IE8 - Win7.ovf"

If successful, the User will be prompted to a VNC connection where the Operating System will be booting. Make sure the drivers get automatically installed (it might require to reboot the OS).

In case of issues, a suggested solution is replacing the video adapter of the virtual machine.

::

  $ virsh -c qemu:///system edit IE8_-_Win7.ovf

Replace the xml attribute `type` of the field `model` in the `video` section from `qxl` to `cirrus`.

Once done, ensure basic things such as Internet connection are working.

Proceed with the desired customisation. As an additional action, install Python3 within the OS. This is not strictly necessary but will help later in the Tutorial.

Make sure the virtualized OS is correctly shut down once done.

The `Virt Manager <https://virt-manager.org/>`_ tool can help to configure and set up the virtual machine.

Configuring SEE
---------------

SEE requires few configuration files to correcly operate.

The libvirt XML configuration related to the imported Windows image must be stored somewhere.

::

  $ virsh --connect qemu:///system list --all
   Id    Name                           State

   -     IE8_-_Win7.ovf                 shut off

  $ virsh --connect qemu:///system dumpxml IE8_-_Win7.ovf >> /home/username/windows7.xml

Then, a JSON file will be used to describe the Context configuration.

::

  /home/username/context.json

  {
      "domain":
      {
          "configuration": "/home/username/windows7.xml"
      },
      "disk":
      {
          "image":
          {
            "uri": "/home/username/images/IE8_-_Win7-disk1.qcow2",
            "provider": "see.image_providers.DummyProvider"
          },
          "clone":
          {
              "storage_pool_path": "/home/username/instances",
              "copy_on_write": true
          }
      }
  }

The following configuration will instruct SEE to create a virtual machine (a domain) using the above mentioned libvirt configuration file.

The domain will use the disk image we just converted. The `clone` field, instructs SEE to make a clone of the given disk. In this way, the running tests will not change or affect the base disk image. The clone will be located in `storage_pool_path` and it will be few Mb in size as `copy_on_write` is enabled.

In case we want to run multiple sandboxes concurrently, might be a good idea to isolate their networks. The `documentation <http://pythonhosted.org/python-see/user.html#network>`_ illustrates how to do so.
