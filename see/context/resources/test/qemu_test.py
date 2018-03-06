import mock
import libvirt
import difflib
import unittest
import xml.etree.ElementTree as etree

from see.context.resources import qemu


def compare(text1, text2):
    """Utility function for comparing text and returining differences."""
    diff = difflib.ndiff(str(text1).splitlines(True), str(text2).splitlines(True))
    return '\n' + '\n'.join(diff)


class DomainXMLTest(unittest.TestCase):
    def test_domain_xml(self):
        """QEMU XML without network."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.qcow2" /></disk></devices></domain>"""
        results = qemu.domain_xml('foo', config, '/diskpath.qcow2')
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_modifies(self):
        """QEMU Fields are modified if existing."""
        config = """<domain><name>bar</name><uuid>bar</uuid><devices><disk device="disk" type="file">""" +\
                 """<source file="/bar"/></disk></devices></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.qcow2" /></disk></devices></domain>"""
        results = qemu.domain_xml('foo', config, '/diskpath.qcow2')
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_network(self):
        """QEMU XML with network fields are modified if existing."""
        config = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/bar" /></disk><interface type="network"><source network="foo" />""" +\
                   """</interface></devices></domain>"""
        results = qemu.domain_xml('foo', config, '/bar', network_name='foo')
        self.assertEqual(results, expected, compare(results, expected))

    def test_domain_xml_network_modifies(self):
        """QEMU XML with network."""
        config = """<domain><devices><interface type="network">""" +\
                 """<source network="bar"/></interface></devices></domain>"""
        expected = """<domain><devices><interface type="network"><source network="foo" /></interface>""" +\
                   """<disk device="disk" type="file"><source file="/bar" /></disk>""" +\
                   """</devices><name>foo</name><uuid>foo</uuid></domain>"""
        results = qemu.domain_xml('foo', config, '/bar', network_name='foo')
        self.assertEqual(results, expected, compare(results, expected))


class DiskXMLTest(unittest.TestCase):
    def test_disk_xml(self):
        """QEMU XML without COW."""
        pool_config = """<pool><target><path>/poolpath</path></target></pool>"""
        disk_config = """<volume><target><path>/path/volume.qcow2</path></target><capacity>10</capacity></volume>"""
        expected = """<volume type="file">
  <name>foo</name>
  <uuid>foo</uuid>
  <target>
    <path>/poolpath/foo.qcow2</path>
    <permissions>
      <mode>0644</mode>
    </permissions>
    <format type="qcow2" />
  </target>
<capacity>10</capacity></volume>"""
        results = qemu.disk_xml('foo', pool_config, disk_config, False)
        self.assertEqual(results, expected, compare(results, expected))

    def test_disk_xml_modifies(self):
        """QEMU XML without COW fields are modified if existing."""
        pool_config = """<pool><target><path>/poolpath</path></target></pool>"""
        disk_config = """<volume><target><path>/path/volume.qcow2</path></target><name>bar</name>""" +\
                      """<capacity>10</capacity></volume>"""
        expected = """<volume type="file">
  <name>foo</name>
  <uuid>foo</uuid>
  <target>
    <path>/poolpath/foo.qcow2</path>
    <permissions>
      <mode>0644</mode>
    </permissions>
    <format type="qcow2" />
  </target>
<capacity>10</capacity></volume>"""
        results = qemu.disk_xml('foo', pool_config, disk_config, False)
        self.assertEqual(results, expected, compare(results, expected))

    def test_disk_cow(self):
        """QEMU XML with COW."""
        pool_config = """<pool><target><path>/poolpath</path></target></pool>"""
        disk_config = """<volume><target><path>/path/volume.qcow2</path></target><capacity>10</capacity></volume>"""
        expected = """<volume type="file"><name>foo</name><uuid>foo</uuid><target>""" +\
                   """<path>/poolpath/foo.qcow2</path><permissions><mode>0644</mode>""" +\
                   """</permissions><format type="qcow2" />""" +\
                   """</target><capacity>10</capacity><backingStore><path>/path/volume.qcow2</path>""" +\
                   """<format type="qcow2" /></backingStore></volume>"""
        results = qemu.disk_xml('foo', pool_config, disk_config, True)
        results = results.replace('\n', '').replace('\t', '').replace('  ', '')
        self.assertEqual(results, expected, compare(results, expected))


class DomainCreateTest(unittest.TestCase):
    def test_create(self):
        """QEMU Create with no network."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.qcow2" /></disk></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.qemu.open', mock.mock_open(read_data=xml), create=True):
            qemu.domain_create(hypervisor, 'foo', {'configuration': '/foo'}, '/diskpath.qcow2')
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))

    def test_create_network(self):
        """QEMU Create with network."""
        xml = """<domain></domain>"""
        expected = """<domain><name>foo</name><uuid>foo</uuid><devices><disk device="disk" type="file">""" +\
                   """<source file="/diskpath.qcow2" /></disk><interface type="network">""" +\
                   """<source network="foo" /></interface></devices></domain>"""
        hypervisor = mock.Mock()
        hypervisor.listNetworks.return_value = []
        with mock.patch('see.context.resources.qemu.open', mock.mock_open(read_data=xml), create=True):
            qemu.domain_create(hypervisor, 'foo', {'configuration': '/foo'}, '/diskpath.qcow2', network_name='foo')
        results = hypervisor.defineXML.call_args_list[0][0][0]
        self.assertEqual(results, expected, compare(results, expected))


class DomainDeleteTest(unittest.TestCase):
    def test_delete_destroy(self):
        """QEMU Domain is destroyed if active."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        qemu.domain_delete(domain, logger)
        self.assertTrue(domain.destroy.called)

    def test_delete_destroy_error(self):
        """QEMU Domain destroy raises error."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = True
        domain.destroy.side_effect = libvirt.libvirtError("BOOM")
        qemu.domain_delete(domain, logger)
        self.assertTrue(domain.undefineFlags.called)

    def test_delete_undefine(self):
        """QEMU Domain is undefined."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        qemu.domain_delete(domain, logger)
        self.assertTrue(domain.undefineFlags.called)

    def test_delete_undefine_snapshots(self):
        """QEMU Domain undefine with snapshots metadata."""
        domain = mock.Mock()
        logger = mock.Mock()
        domain.isActive.return_value = False
        qemu.domain_delete(domain, logger)
        domain.undefineFlags.assert_called_with(libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA)


class PoolCreateTest(unittest.TestCase):
    @mock.patch('os.makedirs')
    @mock.patch('os.path.exists')
    def test_create(self, exists_mock, makedirs):
        """QEMU Create Pool."""
        expected = """<pool type='dir'><name>foo</name><uuid>foo</uuid><target>""" +\
                   """<path>/pool/path/foo</path></target></pool>"""
        hypervisor = mock.Mock()
        exists_mock.return_value = False
        qemu.pool_create(hypervisor, 'foo', '/pool/path')
        results = hypervisor.storagePoolCreateXML.call_args_list[0][0][0]
        results = results.replace('\n', '').replace('\t', '').replace('  ', '')
        makedirs.assert_called_with('/pool/path/foo')
        self.assertEqual(results, expected, compare(results, expected))


class PoolDeleteTest(unittest.TestCase):
    def test_delete_destroy(self):
        """QEMU Pool is destroyed."""
        pool = mock.MagicMock()
        logger = mock.Mock()
        pool.XMLDesc.return_value = """<pool><path>/foo/bar</path></pool>"""
        qemu.pool_delete(pool, logger)
        self.assertTrue(pool.destroy.called)

    def test_volume_deletion(self):
        """QEMU If volumes are contained within the Pool they are deleted."""
        pool = mock.MagicMock()
        logger = mock.Mock()
        volumes = {'foo': mock.Mock(), 'bar': mock.Mock(), 'baz': mock.Mock()}
        pool.XMLDesc.return_value = """<pool><path>/foo/bar</path></pool>"""
        pool.listVolumes.return_value = ('foo', 'bar', 'baz')
        pool.storageVolLookupByName.side_effect = lambda n: volumes[n]
        qemu.pool_delete(pool, logger)
        volumes['foo'].delete.assert_called_with(0)
        volumes['bar'].delete.assert_called_with(0)
        volumes['baz'].delete.assert_called_with(0)

    def test_volume_deletion_error(self):
        """QEMU The failure of deletion of a Volume does not stop the deletion process."""
        pool = mock.MagicMock()
        logger = mock.Mock()
        volumes = {'foo': mock.Mock(), 'bar': mock.Mock(), 'baz': mock.Mock()}
        pool.XMLDesc.return_value = """<pool><path>/foo/bar</path></pool>"""
        pool.listVolumes.return_value = ('foo', 'bar', 'baz')
        pool.storageVolLookupByName.side_effect = lambda n: volumes[n]
        volumes['foo'].delete.side_effect = libvirt.libvirtError('BOOM')
        qemu.pool_delete(pool, logger)
        volumes['foo'].delete.assert_called_with(0)
        volumes['bar'].delete.assert_called_with(0)
        volumes['baz'].delete.assert_called_with(0)
        self.assertTrue(pool.destroy.called)

    @mock.patch('shutil.rmtree')
    @mock.patch('os.path.exists')
    def test_delete_pool_folder(self, os_mock, rm_mock):
        """QEMU Pool's folder is deleted after Pool's deletion."""
        pool = mock.MagicMock()
        logger = mock.Mock()
        os_mock.return_value = True
        pool.XMLDesc.return_value = """<pool><path>/foo/bar/baz</path></pool>"""
        qemu.pool_delete(pool, logger)
        rm_mock.assert_called_with('/foo/bar/baz')

    @mock.patch('shutil.rmtree')
    @mock.patch('os.path.exists')
    def test_delete_pool_folder_error(self, os_mock, rm_mock):
        """QEMU Pool's folder is deleted in case of error."""
        pool = mock.MagicMock()
        logger = mock.Mock()
        os_mock.return_value = True
        pool.XMLDesc.return_value = """<pool><path>/foo/bar/baz</path></pool>"""
        pool.destroy.side_effect = libvirt.libvirtError('BOOM')
        qemu.pool_delete(pool, logger)
        rm_mock.assert_called_with('/foo/bar/baz')


class DiskCloneTest(unittest.TestCase):
    @mock.patch('os.path.exists')
    def test_clone_fwdslash(self, os_mock):
        """QEMU Clone no COW."""
        os_mock.return_value = True
        logger = mock.Mock()
        pool = mock.Mock()
        volume = mock.Mock()
        hypervisor = mock.Mock()
        hypervisor.storageVolLookupByPath.side_effect = libvirt.libvirtError('BAM!')
        pool.XMLDesc.return_value = """<pool><target><path>/pool/path</path></target></pool>"""
        volume.XMLDesc.return_value = """<volume><target><path>/path/volume.qcow2</path>""" +\
                                      """</target><capacity>10</capacity></volume>"""
        expected = """<volume type="file"><name>foo</name><uuid>foo</uuid><target>""" +\
                   """<path>/pool/path/foo.qcow2</path><permissions>""" +\
                   """<mode>0644</mode></permissions>""" +\
                   """<format type="qcow2" /></target>""" +\
                   """<capacity>10</capacity></volume>"""
        with self.assertRaises(libvirt.libvirtError) as error:
            qemu.disk_clone(hypervisor, 'foo', pool, {}, '/foo/bar/baz.qcow2', logger)
        self.assertFalse('/' in etree.fromstring(hypervisor.storagePoolDefineXML.call_args[0][0]).find('.//name').text)

    def test_clone(self):
        """QEMU Clone no COW."""
        logger = mock.Mock()
        pool = mock.Mock()
        volume = mock.Mock()
        hypervisor = mock.Mock()
        hypervisor.storageVolLookupByPath.return_value = volume
        pool.XMLDesc.return_value = """<pool><target><path>/pool/path</path></target></pool>"""
        volume.XMLDesc.return_value = """<volume><target><path>/path/volume.qcow2</path>""" +\
                                      """</target><capacity>10</capacity></volume>"""
        expected = """<volume type="file"><name>foo</name><uuid>foo</uuid><target>""" +\
                   """<path>/pool/path/foo.qcow2</path><permissions>""" +\
                   """<mode>0644</mode></permissions>""" +\
                   """<format type="qcow2" /></target>""" +\
                   """<capacity>10</capacity></volume>"""
        qemu.disk_clone(hypervisor, 'foo', pool, {}, '/foo/bar/baz.qcow2', logger)
        results = pool.createXMLFrom.call_args_list[0][0][0]
        results = results.replace('\n', '').replace('\t', '').replace('  ', '')
        self.assertEqual(results, expected, compare(results, expected))

    def test_clone_cow(self):
        """QEMU Clone with COW."""
        logger = mock.Mock()
        pool = mock.Mock()
        volume = mock.Mock()
        hypervisor = mock.Mock()
        hypervisor.storageVolLookupByPath.return_value = volume
        pool.XMLDesc.return_value = """<pool><target><path>/pool/path</path></target></pool>"""
        volume.XMLDesc.return_value = """<volume><target><path>/path/volume.qcow2</path></target>""" +\
                                      """<capacity>10</capacity></volume>"""
        expected = """<volume type="file"><name>foo</name><uuid>foo</uuid><target>""" +\
                   """<path>/pool/path/foo.qcow2</path><permissions><mode>0644</mode></permissions>""" +\
                   """<format type="qcow2" /></target><capacity>10</capacity>""" +\
                   """<backingStore><path>/path/volume.qcow2</path><format type="qcow2" />""" +\
                   """</backingStore></volume>"""
        qemu.disk_clone(hypervisor, 'foo', pool, {'copy_on_write': True}, '/foo/bar/baz.qcow2', logger)
        results = pool.createXML.call_args_list[0][0][0]
        results = results.replace('\n', '').replace('\t', '').replace('  ', '')
        self.assertEqual(results, expected, compare(results, expected))

    def test_clone_error(self):
        """QEMU RuntimeError is raised if the base image is not contained within a libvirt Pool."""
        logger = mock.Mock()
        pool = mock.Mock()
        hypervisor = mock.Mock()
        hypervisor.storageVolLookupByPath.side_effect = libvirt.libvirtError('BOOM')
        with self.assertRaises(RuntimeError) as error:
            qemu.disk_clone(hypervisor, 'foo', pool, {}, '/foo/bar/baz.qcow2', logger)
            self.assertEqual(str(error), "/foo/bar/baz.qcow2 disk must be contained in a libvirt storage pool.")


@mock.patch('see.context.resources.qemu.network')
class ResourcesTest(unittest.TestCase):
    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    def test_allocate_default(self, create_mock, libvirt_mock, network_mock):
        """QEMU Resources allocator with no extra value and old style image definition."""
        network_mock.lookup.return_value = None
        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'disk': {'image': '/foo/bar'}})
        resources.allocate()
        libvirt_mock.open.assert_called_with('qemu:///system')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar',
                                       '/foo/bar', network_name=None)

    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    def test_allocate_dummy_provider(self, create_mock, libvirt_mock, network_mock):
        """QEMU Resources allocator with no extra value and dummy image provider."""
        network_mock.lookup.return_value = None
        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'disk': {'image': {'uri': '/foo/bar',
                                                                  'provider': 'see.image_providers.DummyProvider'}}})
        resources.allocate()
        libvirt_mock.open.assert_called_with('qemu:///system')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar',
                                       '/foo/bar', network_name=None)

    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    def test_allocate_hypervisor(self, create_mock, libvirt_mock, network_mock):
        """QEMU Resources allocator with hypervisor."""
        network_mock.lookup.return_value = None
        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'hypervisor': 'baz',
                                               'disk': {'image': '/foo/bar'}})
        resources.allocate()
        libvirt_mock.open.assert_called_with('baz')
        create_mock.assert_called_with(resources.hypervisor, 'foo',
                                       'bar', '/foo/bar', network_name=None)

    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    @mock.patch('see.context.resources.qemu.disk_clone')
    @mock.patch('see.context.resources.qemu.pool_create')
    def test_allocate_clone(self, pool_mock, disk_mock, create_mock,
                            libvirt_mock, network_mock):
        """QEMU Resources allocator with disk cloning."""
        pool = mock.MagicMock()
        pool_mock.return_value = pool
        volume = mock.Mock()
        volume.path.return_value = '/foo/bar'
        pool.storageVolLookupByName.return_value = volume
        network_mock.lookup.return_value = None
        resources = qemu.QEMUResources('foo',
                                       {'domain': 'bar',
                                        'disk':
                                        {'image': '/foo/bar.qcow2',
                                         'clone':
                                         {'storage_pool_path': '/baz'}}})
        resources.allocate()
        pool_mock.assert_called_with(resources.hypervisor, 'foo', '/baz')
        disk_mock.assert_called_with(resources.hypervisor, 'foo', pool,
                                     {'storage_pool_path': '/baz'},
                                     '/foo/bar.qcow2', mock.ANY)
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar',
                                       '/foo/bar', network_name=None)

    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    def test_allocate_network(self, create_mock, libvirt_mock, network_mock):
        """QEMU Resources allocator with network."""
        network = mock.Mock()
        network.name.return_value = 'baz'
        network_mock.lookup = mock.Mock()
        network_mock.create.return_value = network

        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'network': 'baz',
                                               'disk': {'image': '/foo/bar'}})
        resources.allocate()
        network_mock.create.assert_called_with(resources.hypervisor, 'foo',
                                               'baz')
        create_mock.assert_called_with(resources.hypervisor, 'foo', 'bar',
                                       '/foo/bar', network_name='baz')

    @mock.patch('see.context.resources.qemu.libvirt')
    @mock.patch('see.context.resources.qemu.domain_create')
    def test_allocate_fail(self, create_mock, libvirt_mock, network_mock):
        """QEMU network is destroyed on allocation fail."""
        network = mock.Mock()
        network.name.return_value = 'baz'
        network_mock.lookup = mock.Mock()
        network_mock.create.return_value = network

        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'network': 'baz',
                                               'disk': {'image': '/foo/bar'}})
        create_mock.side_effect = libvirt.libvirtError('BOOM')
        with self.assertRaises(libvirt.libvirtError):
            resources.allocate()

        resources.deallocate()

        network_mock.delete.assert_called_with(resources.network)

    @mock.patch('see.context.resources.qemu.pool_delete')
    @mock.patch('see.context.resources.qemu.domain_delete')
    def test_deallocate_no_creation(self, delete_mock, pool_delete_mock,
                                    network_mock):
        """QEMU Resources are released on deallocate network and Pool not created."""
        resources = qemu.QEMUResources('foo', {'domain': 'bar',
                                               'disk': {'image': '/foo/bar'}})
        resources._domain = mock.Mock()
        resources._network = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources._storage_pool = mock.Mock()
        resources.deallocate()
        delete_mock.assert_called_with(resources.domain, mock.ANY)
        self.assertFalse(pool_delete_mock.called)
        self.assertFalse(network_mock.delete.called)
        self.assertTrue(resources._hypervisor.close.called)

    @mock.patch('see.context.resources.qemu.pool_delete')
    @mock.patch('see.context.resources.qemu.domain_delete')
    def test_deallocate_creation(self, delete_mock, pool_delete_mock,
                                 network_mock):
        """QEMU Resources are released on deallocate. Network and Pool created."""
        resources = qemu.QEMUResources('foo',
                                       {'domain': 'bar',
                                        'network': {},
                                        'disk': {'image': '/foo/bar',
                                                 'clone':
                                                 {'storage_pool_path': 'foo'}}})
        resources._domain = mock.Mock()
        resources._network = mock.Mock()
        resources._hypervisor = mock.Mock()
        resources._storage_pool = mock.Mock()
        resources.deallocate()
        delete_mock.assert_called_with(resources.domain, mock.ANY)
        network_mock.delete.assert_called_with(resources.network)
        pool_delete_mock.assert_called_with(resources.storage_pool, mock.ANY)
