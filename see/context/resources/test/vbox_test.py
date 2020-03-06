import sys
import mock
import libvirt
import difflib
import unittest

from see.context.resources import vbox


def compare(text1, text2):
    """Utility function for comparing text and returining differences."""
    diff = difflib.ndiff(text1.splitlines(True), text2.splitlines(True))
    return '\n' + '\n'.join(diff)


class DomainXMLTest(unittest.TestCase):
    def test_domain_xml(self):
        """VBOX Domain XML."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.vdi" /></disk></devices></domain>"""
        results = vbox.domain_xml('foo', config, '/diskpath.vdi')
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_modifies(self):
        """VBOX Fields are modified if existing."""
        config = """<domain><name>bar</name><uuid>bar</uuid><devices><disk device="disk" type="file">""" +\
                 """<source file="/bar"/></disk></devices></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.vdi" /></disk></devices></domain>"""
        results = vbox.domain_xml('foo', config, '/diskpath.vdi')
        self.assertEqual(results, expected, compare(results, expected))


class DomainCreateTest(unittest.TestCase):
    def test_create(self):
        """VBOX Create domain."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.vdi" /></disk></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.vbox.open', mock.mock_open(read_data=xml), create=True):
            vbox.domain_create(hypervisor, 'foo', {'configuration': '/foo'}, '/diskpath.vdi')
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))


class DomainDeleteTest(unittest.TestCase):
    def test_delete_destroy(self):
        """VBOX Domain is destroyed if active."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        vbox.domain_delete(domain, logger)
        self.assertTrue(domain.destroy.called)

    def test_delete_destroy_error(self):
        """VBOX Domain destroy raises error."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        domain.destroy.side_effect = libvirt.libvirtError("BOOM")
        vbox.domain_delete(domain, logger)
        self.assertTrue(domain.undefine.called)

    def test_delete_undefine(self):
        """VBOX Domain is undefined."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        vbox.domain_delete(domain, logger)
        self.assertTrue(domain.undefine.called)

    def test_delete_undefine_snapshots(self):
        """VBOX Domain undefine with snapshots metadata."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        domain.undefine.side_effect = libvirt.libvirtError("BOOM")
        vbox.domain_delete(domain, logger)
        domain.undefineFlags.assert_called_with(libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA)


class ResourcesTest(unittest.TestCase):
    if sys.version_info.major >= 3:
        builtin_module = 'builtins'
    else:
        builtin_module = '__builtin__'

    @mock.patch('see.context.resources.vbox.libvirt')
    @mock.patch('see.context.resources.vbox.domain_create')
    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    def test_allocate_default(self, _, create_mock, libvirt_mock):
        """VBOX Resources allocater with no extra value."""
        resources = vbox.VBoxResources('foo',
                                       {'domain': 'bar',
                                        'disk': {'image': '/foo/bar'}})
        resources.allocate()
        libvirt_mock.open.assert_called_with('vbox:///session')
        create_mock.assert_called_with(resources.hypervisor, 'foo',
                                       'bar', '/foo/bar')

    @mock.patch('see.context.resources.vbox.libvirt')
    @mock.patch('see.context.resources.vbox.domain_create')
    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    def test_allocate_hypervisor(self, _, create_mock, libvirt_mock):
        """VBOX Resources allocater with hypervisor."""
        resources = vbox.VBoxResources('foo', {'domain': 'bar',
                                               'hypervisor': 'baz',
                                               'disk': {'image': '/foo/bar'}})
        resources.allocate()
        libvirt_mock.open.assert_called_with('baz')
        create_mock.assert_called_with(resources.hypervisor, 'foo',
                                       'bar', '/foo/bar')

    @mock.patch('see.context.resources.vbox.libvirt')
    @mock.patch('see.context.resources.vbox.domain_create')
    @mock.patch('see.context.resources.vbox.domain_delete')
    def test_deallocate(self, delete_mock, create_mock, libvirt_mock):
        """VBOX Resources are released on deallocate."""
        resources = vbox.VBoxResources('foo', {'domain': 'bar',
                                               'disk': {'image': '/foo/bar'}})
        resources._domain = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources.deallocate()
        delete_mock.assert_called_with(resources.domain, mock.ANY)
        self.assertTrue(resources._hypervisor.close.called)
