import mock
import unittest

from see.context.resources.resources import Resources

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


@mock.patch('see.image_providers.GlanceProvider.glance_client')
@mock.patch('see.image_providers.GlanceProvider.keystone_client')
@mock.patch('see.image_providers.os_glance.os.path')
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

    def test_fresh_image_exists(self, os_mock, keystone_mock, glance_mock):
        image = mock.MagicMock()
        image.id = '1'
        image.name = 'TestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        os_mock.exists.return_value = True
        os_mock.isfile.return_value = True
        os_mock.getmtime.return_value = 32503680000.0  # Jan 1st, 3000

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_not_called()

    def test_image_does_not_exist(self, os_mock, keystone_mock, glance_mock):
        image = mock.MagicMock()
        image.id = '1'
        image.name = 'NonRequestedTestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        resources = Resources('foo', self.config)
        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    @mock.patch('__builtin__.open')
    def test_stale_image_exists(self, open_mock, os_mock, keystone_mock, glance_mock):
        image = mock.MagicMock()
        image.id = '1'
        image.name = 'TestImageName'
        image.updated_at = '2017-02-14T00:00:00Z'
        glance_mock.images.list.return_value = [image]

        os_mock.exists.return_value = True
        os_mock.isfile.return_value = True
        os_mock.isdir.return_value = False
        os_mock.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('1')

    @mock.patch('__builtin__.open')
    def test_newer_image_exists(self, open_mock, os_mock, keystone_mock, glance_mock):
        image1 = mock.MagicMock()
        image1.id = '1'
        image1.name = 'TestImageName'
        image1.updated_at = u'2017-02-14T00:00:00Z'
        image2 = mock.MagicMock()
        image2.id = '2'
        image2.name = 'TestImageName'
        image2.updated_at = u'2017-02-15T00:00:00Z'
        glance_mock.images.list.return_value = [image1, image2]

        os_mock.exists.return_value = True
        os_mock.isfile.return_value = False
        os_mock.isdir.return_value = True

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['target_path'] + '/2'

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('2')
