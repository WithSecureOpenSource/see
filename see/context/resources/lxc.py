# Copyright 2015-2016 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""SEE Linux Container Resources.

This module provides an API for creating a virDomain controlling a Linux Container (LXC).

Configuration::
{
  "domain":
  {
    "configuration": "/etc/myconfig/see/domain.xml",
    "filesystem":
    [{
      "source_path": "/srv/containers",
      "target_path": "/"
    },
    {
      "source_path": "/var/log/containers",
      "target_path": "/var/log"
    }]
  }
  "network":
  {
    "configuration": "/etc/myconfig/see/network.xml",
    "ip_autodiscovery": true
  }
}

Domain:

The User must specify the path of the domain XML configuration file for the Linux Container.

The following fields in the configuration file are replaced or added if missing::

 * name
 * uuid
 * devices

The *filesystem* subfield controls the dynamic filesystem provisioning for the linux container.
If provided, it can be a single or a list of mount points which will be provided to the Linux Container.
The mount point is created on the Host side as *source_path*/*environment_uuid* and will be visible
from the Linux Container as *target_path*.

If the *network* section is provided, the domain will be provided of an interface connected to the specified network.

Network::

Please refer to see.resources.network module.

"""

import os
import shutil
import libvirt
import xml.etree.ElementTree as etree

from see.context.resources import network
from see.context.resources import resources
from see.context.resources.helpers import subelement


def mountpoint(mount, identifier):
    source_path = os.path.join(mount['source_path'], identifier)
    os.makedirs(source_path)

    return (source_path, mount['target_path'])


def domain_xml(identifier, xml, mounts, network_name=None):
    """Fills the XML file with the required fields.

    @param identifier: (str) UUID of the Environment.
    @param xml: (str) XML configuration of the domain.
    @param filesystem: (tuple) ((source, target), (source, target))

     * name
     * uuid
     * devices
     * network
     * filesystem

    """
    domain = etree.fromstring(xml)

    subelement(domain, './/name', 'name', identifier)
    subelement(domain, './/uuid', 'uuid', identifier)
    devices = subelement(domain, './/devices', 'devices', None)

    for mount in mounts:
        filesystem = etree.SubElement(devices, 'filesystem', type='mount')
        etree.SubElement(filesystem, 'source', dir=mount[0])
        etree.SubElement(filesystem, 'target', dir=mount[1])

    if network_name is not None:
        network = subelement(devices, './/interface[@type="network"]', 'interface', None, type='network')
        subelement(network, './/source', 'source', None, network=network_name)

    return etree.tostring(domain).decode('utf-8')


def domain_create(hypervisor, identifier, configuration, network_name=None):
    """libvirt Domain definition.

    @raise: ConfigError, IOError, libvirt.libvirtError.

    """
    mounts = []

    with open(configuration['configuration']) as config_file:
        domain_config = config_file.read()

    if 'filesystem' in configuration:
        if isinstance(configuration['filesystem'], (list, tuple)):
            for mount in configuration['filesystem']:
                mounts.append(mountpoint(mount, identifier))
        else:
            mounts.append(mountpoint(configuration['filesystem'], identifier))

    xml_config = domain_xml(identifier, domain_config, tuple(mounts), network_name=network_name)

    return hypervisor.defineXML(xml_config)


def domain_delete(domain, logger, filesystem):
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
            logger.exception("Unable to undefine the domain.")
        try:
            if filesystem is not None and os.path.exists(filesystem):
                shutil.rmtree(filesystem)
        except Exception:
            logger.exception("Unable to remove the shared folder.")


class LXCResources(resources.Resources):
    """Libvirt resources wrapper for Linux Containers.

    It wrappes libvirt hypervisor connection, network and domain exposing a clean way to initialize and clean them up.
    Class API is defined in see.context module.

    """
    def __init__(self, identifier, configuration):
        super(LXCResources, self).__init__(identifier, configuration)
        self._domain = None
        self._network = None
        self._hypervisor = None
        self._initialize()

    @property
    def hypervisor(self):
        return self._hypervisor

    @property
    def domain(self):
        return self._domain

    @property
    def network(self):
        return self._network

    def _initialize(self):
        """Initializes libvirt resources."""
        network_name = None
        url = 'hypervisor' in self.configuration and self.configuration['hypervisor'] or 'lxc:///'

        self._hypervisor = libvirt.open(url)
        if 'network' in self.configuration:
            self._network = network.create(self._hypervisor, self.identifier, self.configuration['network'])
            network_name = self._network.name()
        self._domain = domain_create(self._hypervisor, self.identifier, self.configuration['domain'],
                                     network_name=network_name)

    def cleanup(self):
        """Releases all resources."""
        filesystem = None

        if self._domain is not None:
            if 'filesystem' in self.configuration:
                filesystem = os.path.join(self.configuration['filesystem']['source_path'], self.identifier)
            domain_delete(self._domain, self.logger, filesystem)
        if self._network is not None:
            try:
                network.delete(self._network)
            except Exception:
                self.logger.exception("Unable to delete network.")
        if self._hypervisor is not None:
            try:
                self._hypervisor.close()
            except Exception:
                self.logger.exception("Unable to close hypervisor connection.")
