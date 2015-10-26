import mock
import random
import libvirt
import difflib
import unittest
import itertools

from see.context.resources import network


def compare(text1, text2):
    """Utility function for comparing text and returning differences."""
    diff = difflib.ndiff(str(text1).splitlines(True), str(text2).splitlines(True))
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
            """<dhcp><range end="192.168.1.128" start="192.168.1.2" /></dhcp></ip></network>"""
        results = network.network_xml('foo', config, address='192.168.1.1')
        self.assertEqual(results, expected, compare(results, expected))


class ValidAddressTest(unittest.TestCase):
    def test_valid(self):
        """A valid address is retrieved."""
        virnetwork = mock.Mock()
        hypervisor = mock.Mock()
        virnetwork.XMLDesc.side_effect = lambda x: '<a><ip address="192.168.{}.1"/></a>'.format(random.randint(1, 256))
        hypervisor.listNetworks.return_value = ('foo', 'bar', 'baz')
        hypervisor.networkLookupByName.return_value = virnetwork

        self.assertTrue(network.valid_address(hypervisor) in ["192.168.{}.1".format(i) for i in range(1, 256)])

    def test_no_ips(self):
        """RuntimeError is raised if all IPs are taken."""
        counter = itertools.count()
        virnetwork = mock.Mock()
        hypervisor = mock.Mock()
        virnetwork.XMLDesc.side_effect = lambda x: '<a><ip address="192.168.{}.1"/></a>'.format(next(counter))
        hypervisor.listNetworks.return_value = range(0, 256)
        hypervisor.networkLookupByName.return_value = virnetwork

        with self.assertRaises(RuntimeError):
            network.valid_address(hypervisor)


class CreateTest(unittest.TestCase):
    def test_create_no_xml(self):
        """Default XML configuration is used if not provided."""
        expected = """<network><forward mode="nat" /><name>foo</name><uuid>foo</uuid>""" +\
                   """<bridge name="virbr-foo" /></network>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        network.create(hypervisor, 'foo', {})
        results = hypervisor.networkCreateXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_no_xml_too_many_attempts(self):
        """RuntimeError is raised if too many attempt to create a network are made."""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        hypervisor.networkCreateXML.side_effect = libvirt.libvirtError('BOOM')
        with self.assertRaises(RuntimeError) as error:
            network.create(hypervisor, 'foo', {}, max_attempts=1)
            self.assertEqual(str(error), "Too many attempts (1) to get a valid IP address.")

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
