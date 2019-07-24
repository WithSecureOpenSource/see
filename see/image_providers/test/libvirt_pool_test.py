import mock
import libvirt
import unittest

from see.context.resources.resources import Resources
from see.image_providers import libvirt_pool

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


@mock.patch.object(libvirt_pool.libvirt, 'open')
@mock.patch('see.image_providers.libvirt_pool.os.path')
class ImageTest(unittest.TestCase):

    def setUp(self):
        self.config = {
            'disk': {
                'image': {
                    'name': '/foo/bar',
                    'provider': 'see.image_providers.LibvirtPoolProvider',
                    'provider_configuration': {
                        'storage_pool_path': '/nowhere',
                        'hypervisor': 'baz'
                    }
                }
            }
        }

    def test_nonexistent_image(self, os_mock, _):
        os_mock.exists.return_value = False
        resources = Resources('foo', self.config)

        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    def test_image_in_pool(self, os_mock, libvirt_mock):
        volume = mock.MagicMock()
        volume.path.return_value = '/nowhere/foo/bar'
        hypervisor = mock.MagicMock()
        hypervisor.storageVolLookupByPath.return_value = volume
        libvirt_mock.return_value = hypervisor
        os_mock.exists.return_value = True

        resources = Resources('foo', self.config)
        expected_image_path = '%s%s' % (
            self.config['disk']['image'][
                'provider_configuration']['storage_pool_path'],
            self.config['disk']['image']['uri'])

        assert expected_image_path == resources.provider_image

        libvirt_mock.assert_called_with('baz')
        hypervisor.storageVolLookupByPath.assert_called_with(
            expected_image_path)
        hypervisor.storagePoolDefineXML.assert_not_called()

    def test_image_not_in_pool(self, os_mock, libvirt_mock):
        volume = mock.MagicMock()
        volume.path.return_value = '/nowhere/foo/bar'
        pool = mock.MagicMock()
        pool.storageVolLookupByName.return_value = volume
        hypervisor = mock.MagicMock()
        hypervisor.storagePoolDefineXML.return_value = pool
        import see
        hypervisor.storageVolLookupByPath.side_effect = libvirt.libvirtError('BOOM')
        libvirt_mock.return_value = hypervisor
        os_mock.exists.return_value = True

        resources = Resources('foo', self.config)
        expected_image_path = '%s%s' % (
            self.config['disk']['image'][
                'provider_configuration']['storage_pool_path'],
            self.config['disk']['image']['uri'])

        assert expected_image_path == resources.provider_image

        libvirt_mock.assert_called_with('baz')
        pool.assert_has_calls([
            mock.call.setAutostart(True),
            mock.call.create(),
            mock.call.refresh(),
            mock.call.storageVolLookupByName(self.config['disk']['image']['uri'])
        ])
