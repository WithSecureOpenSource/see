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

"""SEE QEMU Resources.

This module provides an API for creating a virDomain controlling a QEMU Virtual Machine.

Configuration::
{
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

If the *network* section is provided, the domain will be provided of an interface connected to the specified network.

Disk:

The Disk section must contain the image field with the absolute path to the disk image file.
The disk image file must be placed in a valid libvirt storage pool.

If the optional parameter clone is provided, the Disk will be cloned in a dedicated storage pool created in
the storage_pool_path directory.

If copy_on_write is set to true the disk will be cloned with QCOW COW strategy, allowing to save disk space.

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


POOL_DEFAULT_CONFIG = """
<pool type='dir'>
  <name>{0}</name>
  <uuid>{0}</uuid>
  <target>
    <path>{1}</path>
  </target>
</pool>
"""

VOLUME_DEFAULT_CONFIG = """
<volume type='file'>
  <name>{0}</name>
  <uuid>{0}</uuid>
  <target>
    <path>{1}</path>
    <permissions>
      <mode>0644</mode>
    </permissions>
    <format type='qcow2'/>
  </target>
</volume>
"""

BACKING_STORE_DEFAULT_CONFIG = """
<backingStore>
  <path>{}</path>
  <format type='qcow2'/>
</backingStore>
"""


def domain_xml(identifier, xml, disk_path, network_name=None):
    """Fills the XML file with the required fields.

     * name
     * uuid
     * devices
     ** disk
     * network

    """
    domain = etree.fromstring(xml)

    subelement(domain, './/name', 'name', identifier)
    subelement(domain, './/uuid', 'uuid', identifier)
    devices = subelement(domain, './/devices', 'devices', None)
    disk = subelement(devices, './/disk', 'disk', None, type='file', device='disk')
    subelement(disk, './/source', 'source', None, file=disk_path)

    if network_name is not None:
        network = subelement(devices, './/interface[@type="network"]', 'interface', None, type='network')
        subelement(network, './/source', 'source', None, network=network_name)

    return etree.tostring(domain).decode('utf-8')


def disk_xml(identifier, pool_xml, base_volume_xml, cow):
    """Clones volume_xml updating the required fields.

     * name
     * target path
     * backingStore

    """
    pool = etree.fromstring(pool_xml)
    base_volume = etree.fromstring(base_volume_xml)
    pool_path = pool.find('.//path').text
    base_path = base_volume.find('.//target/path').text
    target_path = os.path.join(pool_path, '%s.qcow2' % identifier)
    volume_xml = VOLUME_DEFAULT_CONFIG.format(identifier, target_path)
    volume = etree.fromstring(volume_xml)
    base_volume_capacity = base_volume.find(".//capacity")

    volume.append(base_volume_capacity)

    if cow:
        backing_xml = BACKING_STORE_DEFAULT_CONFIG.format(base_path)
        backing_store = etree.fromstring(backing_xml)
        volume.append(backing_store)

    return etree.tostring(volume).decode('utf-8')


def domain_create(hypervisor, identifier, configuration, disk_path, network_name=None):
    """libvirt Domain definition.

    @raise: ConfigError, IOError, libvirt.libvirtError.

    """
    with open(configuration['configuration']) as config_file:
        domain_config = config_file.read()

    xml = domain_xml(identifier, domain_config, disk_path, network_name=network_name)

    return hypervisor.defineXML(xml)


def domain_delete(domain, logger):
    """libvirt domain undefinition.

    @raise: libvirt.libvirtError.

    """
    try:
        if domain.isActive():
            domain.destroy()
    except libvirt.libvirtError:
        logger.exception("Unable to destroy the domain.")
    try:
        domain.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA)
    except libvirt.libvirtError:
        logger.exception("Unable to undefine the domain.")


def pool_create(hypervisor, identifier, pool_path):
    """Storage pool creation.

    The following values are set in the XML configuration:
      * name
      * target/path
      * target/permission/label

    """
    path = os.path.join(pool_path, identifier)

    if not os.path.exists(path):
        os.makedirs(path)

    xml = POOL_DEFAULT_CONFIG.format(identifier, path)

    return hypervisor.storagePoolCreateXML(xml, 0)


def pool_delete(storage_pool, logger):
    """Storage Pool deletion, removes all the created disk images within the pool and the pool itself."""
    path = etree.fromstring(storage_pool.XMLDesc(0)).find('.//path').text

    volumes_delete(storage_pool, logger)

    try:
        storage_pool.destroy()
    except libvirt.libvirtError:
        logger.exception("Unable to delete storage pool.")
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except EnvironmentError:
        logger.exception("Unable to delete storage pool folder.")


def volumes_delete(storage_pool, logger):
    """Deletes all storage volume disks contained in the given storage pool."""
    try:
        for vol_name in storage_pool.listVolumes():
            try:
                vol = storage_pool.storageVolLookupByName(vol_name)
                vol.delete(0)
            except libvirt.libvirtError:
                logger.exception("Unable to delete storage volume %s.", vol_name)
    except libvirt.libvirtError:
        logger.exception("Unable to delete storage volumes.")


def disk_clone(hypervisor, identifier, storage_pool, configuration):
    """Disk image cloning.

    Given an original disk image it clones it into a new one, the clone will be created within the storage pool.

    The following values are set into the disk XML configuration:

      * name
      * target/path
      * target/permission/label
      * backingStore/path if copy on write is enabled

    """
    path = configuration['image']
    cow = 'copy_on_write' in configuration['clone'] and configuration['clone']['copy_on_write'] or False

    try:
        volume = hypervisor.storageVolLookupByPath(path)
    except libvirt.libvirtError:
        raise RuntimeError("%s disk must be contained in a libvirt storage pool." % path)

    xml = disk_xml(identifier, storage_pool.XMLDesc(0), volume.XMLDesc(0), cow)

    if cow:
        storage_pool.createXML(xml, 0)
    else:
        storage_pool.createXMLFrom(xml, volume, 0)


class QEMUResources(resources.Resources):
    """Libvirt resources wrapper for Qemu.

    It wrappes libvirt hypervisor connection, network, domain and storage pool,
    exposing a clean way to initialize and clean them up.

    """
    def __init__(self, identifier, configuration):
        super(QEMUResources, self).__init__(identifier, configuration)
        self._domain = None
        self._network = None
        self._storage_pool = None
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

    @property
    def storage_pool(self):
        return self._storage_pool

    def _initialize(self):
        """Initializes libvirt resources."""
        network_name = None
        url = 'hypervisor' in self.configuration and self.configuration['hypervisor'] or 'qemu:///system'

        self._hypervisor = libvirt.open(url)
        if 'clone' in self.configuration['disk']:
            disk_path = self._clone_disk()
        else:
            disk_path = self.configuration['disk']['image']
        if 'network' in self.configuration:
            self._network = network.create(self._hypervisor, self.identifier, self.configuration['network'])
            network_name = self._network.name()

        self._domain = domain_create(self._hypervisor, self.identifier, self.configuration['domain'],
                                     disk_path, network_name=network_name)

    def _clone_disk(self):
        """Clones the disk and returns the path to the new disk."""
        self._storage_pool = pool_create(self._hypervisor, self.identifier,
                                         self.configuration['disk']['clone']['storage_pool_path'])
        disk_clone(self._hypervisor, self.identifier, self._storage_pool, self.configuration['disk'])
        disk_name = self._storage_pool.listVolumes()[0]
        return self._storage_pool.storageVolLookupByName(disk_name).path()

    def cleanup(self):
        """Releases all resources."""
        if self._domain is not None:
            domain_delete(self._domain, self.logger)
        if self._network is not None:
            self._network_delete()
        if self._storage_pool is not None:
            self._storage_pool_delete()
        if self._hypervisor is not None:
            self._hypervisor_delete()

    def _network_delete(self):
        try:
            network.delete(self._network)
        except Exception:
            self.logger.exception("Unable to delete network.")

    def _storage_pool_delete(self):
        try:
            pool_delete(self._storage_pool, self.logger)
        except Exception:
            self.logger.exception("Unable to delete storage pool.")

    def _hypervisor_delete(self):
        try:
            self._hypervisor.close()
        except Exception:
            self.logger.exception("Unable to close hypervisor connection.")
