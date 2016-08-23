import mock
import random
import libvirt
import difflib
import unittest
import itertools
import ipaddress

from see.context.resources import network


def compare(text1, text2):
    """Utility function for comparing text and returning differences."""
    diff = difflib.ndiff(str(text1).splitlines(True),
                         str(text2).splitlines(True))
    return '\n' + '\n'.join(diff)


class NetworkXMLTest(unittest.TestCase):
    def test_ip(self):
        """XML with given IP."""
        config = """<network>
          <forward mode="nat"/>
          <ip address="192.168.235.1" netmask="255.255.255.0">
            <dhcp>
              <range start="192.168.235.2" end="192.168.235.128"/>
            </dhcp>
          </ip>
        </network>
        """
        expected = """<network>
          <forward mode="nat" />
          <ip address="192.168.235.1" netmask="255.255.255.0">
            <dhcp>
              <range end="192.168.235.128" start="192.168.235.2" />
            </dhcp>
          </ip>
        <name>foo</name><uuid>foo</uuid><bridge name="virbr-foo" /></network>"""
        results = network.network_xml('foo', config)
        self.assertEqual(results, expected, compare(results, expected))

    def test_ip_modifies(self):
        """Name and UUID are modified if existing."""
        config = """<network>
          <name>bar</name>
          <uuid>bar</uuid>
          <bridge name="virbr-bar"/>
          <forward mode="nat"/>
          <ip address="192.168.235.1" netmask="255.255.255.0">
            <dhcp>
              <range start="192.168.235.2" end="192.168.235.128"/>
            </dhcp>
          </ip>
        </network>
        """
        expected = """<network>
          <name>foo</name>
          <uuid>foo</uuid>
          <bridge name="virbr-foo" />
          <forward mode="nat" />
          <ip address="192.168.235.1" netmask="255.255.255.0">
            <dhcp>
              <range end="192.168.235.128" start="192.168.235.2" />
            </dhcp>
          </ip>
        </network>"""
        results = network.network_xml('foo', config)
        self.assertEqual(results, expected, compare(results, expected))

    def test_ip_address(self):
        """RuntimeError is raised if both address and <ip> are specified."""
        config = """<network>
          <forward mode="nat"/>
          <ip address="192.168.235.1" netmask="255.255.255.0">
            <dhcp>
              <range start="192.168.235.2" end="192.168.235.128"/>
            </dhcp>
          </ip>
        </network>
        """
        with self.assertRaises(RuntimeError):
            network.network_xml('foo', config, address=True)

    def test_no_ip_address(self):
        """XML with address."""
        config = """<network>
          <forward mode="nat"/>
        </network>
        """
        expected = """<network>
          <forward mode="nat" />
        <name>foo</name><uuid>foo</uuid><bridge name="virbr-foo" />""" + \
            """<ip address="192.168.1.1" netmask="255.255.255.0">""" + \
            """<dhcp><range end="192.168.1.254" start="192.168.1.2" />""" +\
            """</dhcp></ip></network>"""
        address = ipaddress.IPv4Network(u'192.168.1.0/24')
        results = network.network_xml('foo', config, address=address)
        self.assertEqual(results, expected, compare(results, expected))


class ValidAddressTest(unittest.TestCase):
    def test_valid(self):
        """A valid address is retrieved."""
        virnetwork = mock.Mock()
        hypervisor = mock.Mock()
        virnetwork.XMLDesc.side_effect = (
            lambda x:
            '<a><ip address="192.168.%s.1" netmask="255.255.255.0"/></a>'
            % random.randint(1, 256))
        hypervisor.listNetworks.return_value = ('foo', 'bar', 'baz')
        hypervisor.networkLookupByName.return_value = virnetwork
        configuration = {'ipv4': '192.168.0.0',
                         'prefix': 16,
                         'subnet_prefix': 24}

        self.assertTrue(network.generate_address(hypervisor, configuration) in
                        [ipaddress.IPv4Network(u'192.168.{}.0/24'.format(i))
                         for i in range(1, 256)])

    def test_invalid(self):
        """ValueError is raised if configuration address is invalid."""
        virnetwork = mock.Mock()
        hypervisor = mock.Mock()
        virnetwork.XMLDesc.side_effect = (
            lambda x:
            '<a><ip address="192.168.%s.1" netmask="255.255.255.0"/></a>'
            % random.randint(1, 256))
        hypervisor.listNetworks.return_value = ('foo', 'bar', 'baz')
        hypervisor.networkLookupByName.return_value = virnetwork
        configuration = {'ipv4': '192.168.0.1',
                         'prefix': 16,
                         'subnet_prefix': 24}

        with self.assertRaises(ValueError):
            network.generate_address(hypervisor, configuration)

    def test_no_ip(self):
        """RuntimeError is raised if all IPs are taken."""
        counter = itertools.count()
        virnetwork = mock.Mock()
        hypervisor = mock.Mock()
        virnetwork.XMLDesc.side_effect = (
            lambda x:
            '<a><ip address="192.168.%s.1" netmask="255.255.255.0"/></a>'
            % next(counter))
        hypervisor.listNetworks.return_value = range(0, 256)
        hypervisor.networkLookupByName.return_value = virnetwork
        configuration = {'ipv4': '192.168.0.0',
                         'prefix': 16,
                         'subnet_prefix': 24}

        with self.assertRaises(RuntimeError):
            network.generate_address(hypervisor, configuration)


class CreateTest(unittest.TestCase):
    def test_create_too_many_attempts(self):
        """RuntimeError is raised if too many fails to create a network."""
        xml = '<network><forward mode="nat"/></network>'
        network.MAX_ATTEMPTS = 3
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        hypervisor.networkCreateXML.side_effect = libvirt.libvirtError('BOOM')
        configuration = {'configuration': 'bar',
                         'dynamic_address': {'ipv4': '10.0.0.0',
                                             'prefix': 16,
                                             'subnet_prefix': 24}}

        with mock.patch('see.context.resources.network.open',
                        mock.mock_open(read_data=xml), create=True):
            try:
                network.create(hypervisor, 'foo', configuration)
            except RuntimeError as error:
                self.assertEqual(str(error),
                                 "Exceeded attempts (3) to get IP address.")

    def test_create_xml(self):
        """Provided XML is used."""
        xml = """<network><forward mode="nat"/><ip address="192.168.1.1" netmask="255.255.255.0">""" + \
              """<dhcp><range end="192.168.1.128" start="192.168.1.2"/></dhcp></ip></network>"""
        expected = """<network><forward mode="nat" /><ip address="192.168.1.1" netmask="255.255.255.0">""" + \
            """<dhcp><range end="192.168.1.128" start="192.168.1.2" /></dhcp></ip>""" + \
            """<name>foo</name><uuid>foo</uuid><bridge name="virbr-foo" /></network>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.network.open', mock.mock_open(read_data=xml), create=True):
            network.create(hypervisor, 'foo', {'configuration': '/foo', 'ip_autodiscovery': False})
        results = hypervisor.networkCreateXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_xml_error(self):
        """RuntimeError is raised in case of creation error."""
        xml = """<network><forward mode="nat"/><ip address="192.168.1.1" netmask="255.255.255.0">""" + \
              """<dhcp><range end="192.168.1.128" start="192.168.1.2"/></dhcp></ip></network>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        hypervisor.networkCreateXML.side_effect = libvirt.libvirtError('BOOM')
        with mock.patch('see.context.resources.network.open', mock.mock_open(read_data=xml), create=True):
            with self.assertRaises(RuntimeError) as error:
                network.create(hypervisor, 'foo', {'configuration': '/foo', 'ip_autodiscovery': False})
                self.assertEqual(str(error), "Unable to create new network: BOOM.")

    def test_delete(self):
        """Network is destroyed on delete()."""
        net = mock.Mock()
        network.delete(net)
        self.assertTrue(net.destroy.called)


class LookupTest(unittest.TestCase):
    def test_lookup(self):
        """Network lookup passes correct parameters to hypervisor."""
        xml = """<domain><interface type="network">""" +\
              """<source network="foo" /></interface></domain>"""
        domain = mock.Mock()
        hypervisor = mock.Mock()
        domain.XMLDesc.return_value = xml
        domain.connect.return_value = hypervisor

        network.lookup(domain)
        hypervisor.networkLookupByName.assert_called_with('foo')

    def test_lookup_no_network(self):
        """None is return if domain is not associated with any Network."""
        xml = """<domain></domain>"""
        domain = mock.Mock()
        hypervisor = mock.Mock()
        domain.XMLDesc.return_value = xml
        domain.connect.return_value = hypervisor

        self.assertEqual(network.lookup(domain), None)
