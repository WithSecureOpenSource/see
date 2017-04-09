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

"""SEE Network module.

This module provides an API for creating virNetwork objects through libvirt.

Configuration::

{
    "configuration": "/path/of/network/configuration.xml",
    "dynamic_address":
    {
        "ipv4": "192.168.0.0",
        "prefix": 16,
        "subnet_prefix": 24
    }
}

The User can optionally specify the path of the libvirt XML configuration.

The following fields in the configuration file are added or replaced.

::

 * name
 * uuid
 * bridge

The user can delegate to SEE the generation of a valid address
for the newly created sub-network.
This is useful for running multiple isolated Environments in the same network.

To do so, the dynamic_address field must be provided specifying the network
address and prefix as well as the prefix for the created sub-network.

SEE will generate a libvirt network with a random IP address in the range
specified by the prefix and sub-prefix. The network will have DHCP server
enabled for the guest virtual machines.

In the given example, SEE will provide a random network in the range
192.168.[0-225].0/24 with DHCP server assigning addresses in the range
192.168.[0-225].[2-255].

Setting dynamic_address and providing a <ip> field in the libvirt XML
configuration will cause RuntimeError to be raised.

"""

import random
import ipaddress

from itertools import count
import xml.etree.ElementTree as etree

import libvirt

from see.context.resources.helpers import subelement


def create(hypervisor, identifier, configuration):
    """Creates a virtual network according to the given configuration.

    @param hypervisor: (libvirt.virConnect) connection to libvirt hypervisor.
    @param identifier: (str) UUID for the virtual network.
    @param configuration: (dict) network configuration.

    @return: (libvirt.virNetwork) virtual network.

    """
    counter = count()
    xml_config = DEFAULT_NETWORK_XML

    if not {'configuration', 'dynamic_address'} & set(configuration.keys()):
        raise RuntimeError(
            "Either configuration or dynamic_address must be specified")

    if 'configuration' in configuration:
        with open(configuration['configuration']) as xml_file:
            xml_config = xml_file.read()

    while True:
        if 'dynamic_address' in configuration:
            address = generate_address(hypervisor,
                                       configuration['dynamic_address'])
            xml_string = network_xml(identifier, xml_config, address=address)
        else:
            xml_string = network_xml(identifier, xml_config)

        try:
            return hypervisor.networkCreateXML(xml_string)
        except libvirt.libvirtError as error:
            if next(counter) > MAX_ATTEMPTS:
                raise RuntimeError(
                    "Exceeded failed attempts ({}) to get IP address.".format(
                        MAX_ATTEMPTS),
                    "Last error: {}".format(error))


def lookup(domain):
    """Find the virNetwork object associated to the domain.

    If the domain has more than one network interface,
    the first one is returned.
    None is returned if the domain is not attached to any network.

    """
    xml = domain.XMLDesc(0)
    element = etree.fromstring(xml)
    subelm = element.find('.//interface[@type="network"]')

    if subelm is not None:
        network = subelm.find('.//source').get('network')
        hypervisor = domain.connect()

        return hypervisor.networkLookupByName(network)

    return None


def delete(network):
    """libvirt network cleanup.

    @raise: libvirt.libvirtError.

    """
    try:
        network.destroy()
    except libvirt.libvirtError as error:
        raise RuntimeError("Unable to destroy network: {}".format(error))


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

    Libvirt bridge will have address and DHCP server configured
    according to the subnet prefix length.

    """
    if network.find('.//ip') is not None:
        raise RuntimeError("Address already specified in XML configuration.")

    netmask = str(address.netmask)
    ipv4 = str(address[1])
    dhcp_start = str(address[2])
    dhcp_end = str(address[-2])
    ip = etree.SubElement(network, 'ip', address=ipv4, netmask=netmask)
    dhcp = etree.SubElement(ip, 'dhcp')

    etree.SubElement(dhcp, 'range', start=dhcp_start, end=dhcp_end)


def generate_address(hypervisor, configuration):
    """Generate a valid IP address according to the configuration."""
    ipv4 = configuration['ipv4']
    prefix = configuration['prefix']
    subnet_prefix = configuration['subnet_prefix']
    subnet_address = ipaddress.IPv4Network(u'/'.join((str(ipv4), str(prefix))))
    net_address_pool = subnet_address.subnets(new_prefix=subnet_prefix)

    return address_lookup(hypervisor, net_address_pool)


def address_lookup(hypervisor, address_pool):
    """Retrieves a valid and available network IP address."""
    address_pool = set(address_pool)
    active_addresses = set(active_network_addresses(hypervisor))

    try:
        return random.choice(tuple(address_pool - active_addresses))
    except IndexError:
        raise RuntimeError("All IP addresses are in use")


def active_network_addresses(hypervisor):
    """Query libvirt for the already reserved addresses."""
    active = []

    for network in hypervisor.listNetworks():
        try:
            xml = hypervisor.networkLookupByName(network).XMLDesc(0)
        except libvirt.libvirtError:  # network has been destroyed meanwhile
            continue
        else:
            ip_element = etree.fromstring(xml).find('.//ip')
            address = ip_element.get('address')
            netmask = ip_element.get('netmask')

            active.append(ipaddress.IPv4Network(u'/'.join((address, netmask)),
                                                strict=False))

    return active


MAX_ATTEMPTS = 10
DEFAULT_NETWORK_XML = """
<network>
  <forward mode="nat"/>
</network>
"""
