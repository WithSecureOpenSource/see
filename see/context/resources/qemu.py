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

"""SEE QEMU Resources.

This module provides an API for creating a virDomain controlling
 a QEMU Virtual Machine.

Configuration::
{
  "domain":
  {
    "configuration": "/etc/myconfig/see/domain.xml",
  },
  "disk":
  {
    "image":
    {
      "uri": "image.qcow2",
      "provider": "see.image_providers.LibvirtPoolProvider",
      "provider_configuration": {
        "storage_pool_path": "/var/mystoragepool"
      }
    }
    "clone":
    {
      "storage_pool_path": "/var/data/pools",
      "copy_on_write": true
    }
  },
  "network":
  {
    "configuration": "/path/of/network/configuration.xml",
    "dynamic_address":
    {
      "ipv4": "192.168.0.0",
      "prefix": 16,
      "subnet_prefix": 24
    }
  }
}

Domain:

The User must specify the path of the domain XML configuration file
for the QEMU Virtual Machine.

The following fields in the configuration file are replaced or added if missing.

::

 * name
 * uuid
 * devices

If the *network* section is provided,
the domain will be provided of an interface connected to the specified network.

Disk:

The Disk section must contain the image field with the absolute path
to the disk image file.
The disk image file must be placed in a valid libvirt storage pool.

If the optional parameter clone is provided,
the Disk will be cloned in a dedicated storage pool created
in the storage_pool_path directory.

If copy_on_write is set to true the disk will be cloned with QCOW COW strategy,
allowing to save disk space.

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

BASE_POOL_CONFIG = """
<pool type='dir'>
  <name>{0}</name>
  <target>
    <path>{1}</path>
  </target>
</pool>
"""

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
    disk = subelement(devices, './/disk', 'disk', None, type='file',
                      device='disk')
    subelement(disk, './/source', 'source', None, file=disk_path)

    if network_name is not None:
        net = subelement(devices, './/interface[@type="network"]',
                         'interface', None, type='network')
        subelement(net, './/source', 'source', None, network=network_name)

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

    xml = domain_xml(identifier, domain_config,
                     disk_path, network_name=network_name)

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


def pool_lookup(hypervisor, disk_path):
    """Storage pool lookup.

    Retrieves the the virStoragepool which contains the disk at the given path.

    """
    try:
        volume = hypervisor.storageVolLookupByPath(disk_path)

        return volume.storagePoolLookupByVolume()
    except libvirt.libvirtError:
        return None


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
                logger.exception(
                    "Unable to delete storage volume %s.", vol_name)
    except libvirt.libvirtError:
        logger.exception("Unable to delete storage volumes.")


def disk_clone(hypervisor, identifier, storage_pool, configuration, image, logger):
    """Disk image cloning.

    Given an original disk image it clones it into a new one, the clone will be created within the storage pool.

    The following values are set into the disk XML configuration:

      * name
      * target/path
      * target/permission/label
      * backingStore/path if copy on write is enabled

    """
    cow = configuration.get('copy_on_write', False)

    try:
        volume = hypervisor.storageVolLookupByPath(image)
    except libvirt.libvirtError:
        if os.path.exists(image):
            pool_path = os.path.dirname(image)
            logger.info("LibVirt pool does not exist, creating {} pool".format(
                pool_path.replace('/', '_')))
            pool = hypervisor.storagePoolDefineXML(BASE_POOL_CONFIG.format(
                pool_path.replace('/', '_'), pool_path))
            pool.setAutostart(True)
            pool.create()
            pool.refresh()
            volume = hypervisor.storageVolLookupByPath(image)
        else:
            raise RuntimeError(
                "%s disk does not exist." % image)

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
        self._hypervisor = None
        self._domain = None
        self._network = None
        self._storage_pool = None

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

    def allocate(self):
        """Initializes libvirt resources."""
        network_name = None

        self._hypervisor = libvirt.open(
            self.configuration.get('hypervisor', 'qemu:///system'))

        self._storage_pool = self._retrieve_pool()

        if 'network' in self.configuration:
            self._network = network.create(self._hypervisor, self.identifier,
                                           self.configuration['network'])
            network_name = self._network.name()

        disk_path = self._retrieve_disk_path()

        if self._storage_pool is not None:
            self._storage_pool.refresh()

        self._domain = domain_create(self._hypervisor, self.identifier,
                                     self.configuration['domain'],
                                     disk_path, network_name=network_name)

        if self._network is None:
            self._network = network.lookup(self._domain)

    def deallocate(self):
        """Releases all resources."""
        if self._domain is not None:
            domain_delete(self._domain, self.logger)
        if self._network is not None:
            self._network_delete()
        if self._storage_pool is not None:
            self._storage_pool_delete()
        if self._hypervisor is not None:
            self._hypervisor_delete()

    def _retrieve_pool(self):
        if 'clone' in self.configuration['disk']:
            return pool_create(
                self._hypervisor, self.identifier,
                self.configuration['disk']['clone']['storage_pool_path'])
        else:
            return pool_lookup(self._hypervisor,
                               self.provider_image)

    def _retrieve_disk_path(self):
        if 'clone' in self.configuration['disk']:
            return self._clone_disk(self.configuration['disk']['clone'])
        else:
            return self.provider_image

    def _clone_disk(self, configuration):
        """Clones the disk and returns the path to the new disk."""
        disk_clone(self._hypervisor, self.identifier, self._storage_pool,
                   configuration, self.provider_image, self.logger)
        disk_name = self._storage_pool.listVolumes()[0]

        return self._storage_pool.storageVolLookupByName(disk_name).path()

    def _network_delete(self):
        if 'network' in self.configuration:
            try:
                network.delete(self._network)
            except Exception:
                self.logger.exception("Unable to delete network.")

    def _storage_pool_delete(self):
        if 'clone' in self.configuration.get('disk', {}):
            try:
                pool_delete(self._storage_pool, self.logger)
            except Exception:
                self.logger.exception("Unable to delete storage pool.")

    def _hypervisor_delete(self):
        try:
            self._hypervisor.close()
        except Exception:
            self.logger.exception("Unable to close hypervisor connection.")
