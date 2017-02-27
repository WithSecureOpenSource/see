import mock
import unittest

from see.context.resources.resources import Resources

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


@mock.patch('see.image_providers.GlanceProvider.keystone_client')
@mock.patch('see.image_providers.os_glance.os')
@mock.patch('see.image_providers.GlanceProvider.glance_client')
class ImageTest(unittest.TestCase):

    def setUp(self):
        self.config = {
            'disk': {
                'image': {
                    'uri': 'TestImageName',
                    'provider': 'see.image_providers.GlanceProvider',
                    'provider_configuration': {
                        'target_path': '/foo/bar',
                        'glance_url': '/glance/baz',
                        'os_auth': {
                            'username': 'dummy',
                            'password': 'dmpwd'
                        }
                    }
                }
            }
        }

    def test_fresh_image_exists(self, glance_mock, os_mock, _):
        image = mock.MagicMock()
        image.id = '1'
        image.name = 'TestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 32503680000.0  # Jan 1st, 3000

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_not_called()

    def test_image_does_not_exist(self, glance_mock, *_):
        image = mock.MagicMock()
        image.id = '1'
        image.name = 'NonRequestedTestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        resources = Resources('foo', self.config)
        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    @mock.patch('__builtin__.open', new_callable=mock.mock_open)
    @mock.patch('see.image_providers.os_glance.hashlib')
    def test_stale_image_exists(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        image = mock.MagicMock()
        image.id = '1'
        image.checksum = '1111'
        image.name = 'TestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1111'
        hashlib_mock.md5.return_value = md5

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.isdir.return_value = False
        os_mock.path.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('1')
        self.assertTrue([mock.call(expected_image_path, 'wb'),
                         mock.call(expected_image_path, 'rb')],
                        open_mock.call_args_list)
        os_mock.remove.assert_not_called()

    @mock.patch('__builtin__.open', new_callable=mock.mock_open)
    @mock.patch('see.image_providers.os_glance.hashlib')
    def test_same_name_images_exist(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        image1 = mock.MagicMock()
        image1.id = '1'
        image1.checksum = '1111'
        image1.name = 'TestImageName'
        image1.updated_at = u'2017-02-14T00:00:00Z'
        image2 = mock.MagicMock()
        image2.id = '2'
        image2.checksum = '2222'
        image2.name = 'TestImageName'
        image2.updated_at = u'2017-02-15T00:00:00Z'
        glance_mock.images.list.return_value = [image1, image2]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '2222'
        hashlib_mock.md5.return_value = md5

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = False
        os_mock.path.isdir.return_value = True

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path'] + '/2'

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('2')
        self.assertTrue([mock.call(expected_image_path, 'wb'),
                         mock.call(expected_image_path, 'rb')],
                        open_mock.call_args_list)
        os_mock.remove.assert_not_called()

    @mock.patch('__builtin__.open', new_callable=mock.mock_open)
    @mock.patch('see.image_providers.os_glance.hashlib')
    def test_checksum_mismatch(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        image = mock.MagicMock()
        image.id = '1'
        image.checksum = '1111'
        image.name = 'TestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1234'
        hashlib_mock.md5.return_value = md5

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.isdir.return_value = False
        os_mock.path.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path']

        with self.assertRaisesRegexp(RuntimeError, 'Checksum failure. File: '):
            assert resources.provider_image == expected_image_path

        glance_mock.images.data.assert_called_with('1')
        self.assertTrue([mock.call(expected_image_path, 'wb'),
                         mock.call(expected_image_path, 'rb')],
                        open_mock.call_args_list)
        os_mock.remove.assert_called_once_with(expected_image_path)
