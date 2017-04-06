# Copyright 2015-2017 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""SEE VirtualBox Resources.

This module provides an API for creating a virDomain controlling a VirtualBox Virtual Machine.

Configuration::
{
  "domain":
  {
    "configuration": "/etc/myconfig/see/domain.xml",
  },
  "disk":
  {
     "image": {
        "uri": "/var/mystoragepool/image.vdi",
        "provider": "see.image_providers.DummyProvider"
     }
  }
}

Domain:

The User must specify the path of the domain XML configuration file for the Linux Container.

The following fields in the configuration file are replaced or added if missing::

 * name
 * uuid
 * devices

Disk:

The Disk section must contain the image field with the absolute path to the disk image file.

"""

import libvirt
import xml.etree.ElementTree as etree

from see.context.resources import resources
from see.context.resources.helpers import subelement


def domain_xml(identifier, xml, disk_path):
    """Fills the XML file with the required fields.

     * name
     * uuid
     * devices

    """
    domain = etree.fromstring(xml)

    subelement(domain, './/name', 'name', identifier)
    subelement(domain, './/uuid', 'uuid', identifier)
    devices = subelement(domain, './/devices', 'devices', None)
    disk = subelement(devices, './/disk', 'disk', None, type='file', device='disk')
    subelement(disk, './/source', 'source', None, file=disk_path)

    return etree.tostring(domain).decode('utf-8')


def domain_create(hypervisor, identifier, configuration, disk_path):
    """libvirt Domain definition.

    @raise: ConfigError, IOError, libvirt.libvirtError.

    """
    with open(configuration['configuration']) as config_file:
        domain_config = config_file.read()

    xml = domain_xml(identifier, domain_config, disk_path)

    return hypervisor.defineXML(xml)


def domain_delete(domain, logger):
    """libvirt domain undefinition.

    @raise: libvirt.libvirtError.

    """
    if domain is not None:
        try:
            if domain.isActive():
                domain.destroy()
        except libvirt.libvirtError:
            logger.exception("Unable to destroy the domain.")
        try:
            domain.undefine()
        except libvirt.libvirtError:
            try:
                domain.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA)  # domain with snapshots
            except libvirt.libvirtError:
                logger.exception("Unable to undefine the domain.")


class VBoxResources(resources.Resources):
    """Libvirt resources wrapper for Virtualbox.

    It wrappes libvirt hypervisor connection and domain,
    exposing a clean way to initialize and clean them up.

    """
    def __init__(self, identifier, configuration):
        super(VBoxResources, self).__init__(identifier, configuration)
        self._domain = None
        self._hypervisor = None

    @property
    def hypervisor(self):
        return self._hypervisor

    @property
    def domain(self):
        return self._domain

    def allocate(self):
        """Initializes libvirt resources."""
        disk_path = self.provider_image

        self._hypervisor = libvirt.open(
            self.configuration.get('hypervisor', 'vbox:///session'))

        self._domain = domain_create(self._hypervisor, self.identifier,
                                     self.configuration['domain'], disk_path)

    def deallocate(self):
        """Releases all resources."""
        if self._domain is not None:
            domain_delete(self._domain, self.logger)
        if self._hypervisor is not None:
            try:
                self._hypervisor.close()
            except Exception:
                self.logger.exception("Unable to close hypervisor connection.")
