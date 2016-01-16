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

"""SEE Network module.

This module provides an API for creating virNetwork objects through libvirt.

Configuration::

{
    "configuration": "/path/of/network/configuration.xml",
    "ip_autodiscovery": true
}

The User can specify the path in which a custom XML configuration is stored, if not provided DEFAULT_CONFIG
will be used.

The following fields in the configuration file are replaced or added if missing::

 * name
 * uuid
 * bridge

If IP autodiscovery is set to True, the module will provide a valid IP address to the network in the range
192.168.1.1 - 192.168.255.1. A DHCP server will be added as well giving addresses in range 192.168.X.2 - 192.168.X.128.

Setting ip_autodiscovery True and providing a <ip> field in the custom XML file will cause RuntimeError to be raised.

"""


import libvirt
import xml.etree.ElementTree as etree

from see.context.resources.helpers import subelement


DEFAULT_CONFIG = """<network><forward mode="nat"/></network>"""


def network_xml(identifier, xml, address=None):
    """Fills the XML file with the required fields.

     * name
     * uuid
     * bridge
     * ip
     ** dhcp

    """
    netname = identifier[:8]
    network = etree.fromstring(xml)

    subelement(network, './/name', 'name', identifier)
    subelement(network, './/uuid', 'uuid', identifier)
    subelement(network, './/bridge', 'bridge', None, name='virbr-%s' % netname)

    if address is not None:
        set_address(network, address)

    return etree.tostring(network).decode('utf-8')


def set_address(network, address):
    """Sets the given address to the network XML element.

    A DHCP subelement is added, DHCP range is set between X.X.X.2 to X.X.X.128.

    """
    if network.find('.//ip') is None:
        ip = etree.SubElement(network, 'ip', address=address, netmask='255.255.255.0')
        dhcp_addr = address[:len(address) - 1]
        dhcp = etree.SubElement(ip, 'dhcp')
        etree.SubElement(dhcp, 'range', start=dhcp_addr + '2', end=dhcp_addr + '128')
    else:
        raise RuntimeError("Using IP autodiscovery with IP already set in XML configuration.")


def valid_address(hypervisor):
    """Retrieves a valid, available IP."""
    address_pool = set(['192.168.%s.1' % x for x in range(0, 255)])
    active = active_addresses(hypervisor)

    try:
        return address_pool.difference(set(active)).pop()
    except KeyError:
        raise RuntimeError("All IP addresses are in use")


def active_addresses(hypervisor):
    """Looks up from the existing network the already reserved IP addresses."""
    active = []

    for network in hypervisor.listNetworks():
        try:
            xml = hypervisor.networkLookupByName(network).XMLDesc(0)
            address = etree.fromstring(xml).find('.//ip').get('address')
            active.append(address)
        except libvirt.libvirtError:  # race condition handling: the network has been destroyed meanwhile
            continue

    return active


def create(hypervisor, identifier, configuration, max_attempts=10):
    """Creates a virtual network according to the given configuration.

    @param hypervisor: (libvirt.virConnect) connection to libvirt hypervisor.
    @param identifier: (str) UUID for the virtual network.
    @param configuration: (dict) network configuration.
    @param max_attempts: (int) maximum amount of attempts retrieving a free IP address.
      Valid only if IP autodiscovery is set in configuration.
    @return: (libvirt.virNetwork) virtual network.

    """
    autodiscovery = 'ip_autodiscovery' in configuration and configuration['ip_autodiscovery'] or False
    if 'configuration' in configuration:
        with open(configuration['configuration']) as config_file:
            network_config = config_file.read()
    else:
        network_config = DEFAULT_CONFIG

    if autodiscovery:
        for attempt in range(max_attempts):
            address = valid_address(hypervisor)
            xml = network_xml(identifier, network_config, address)
            try:
                return hypervisor.networkCreateXML(xml)
            except libvirt.libvirtError:  # race condition: another Environment took the same IP
                continue
        else:
            raise RuntimeError("Too many attempts ({}) to get a valid IP address.".format(max_attempts))
    else:
        xml = network_xml(identifier, network_config)
        try:
            return hypervisor.networkCreateXML(xml)
        except libvirt.libvirtError as error:
            raise RuntimeError("Unable to create new network: {}".format(error))


def delete(network):
    """libvirt network cleanup.

    @raise: libvirt.libvirtError.

    """
    try:
        network.destroy()
    except libvirt.libvirtError as error:
        raise RuntimeError("Unable to destroy network: {}".format(error))
