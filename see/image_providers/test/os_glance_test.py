import os
import sys
import mock
import unittest

from see.context.resources.resources import Resources

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


@mock.patch('see.image_providers.GlanceProvider.os_session')
@mock.patch('see.image_providers.os_glance.os')
@mock.patch('see.image_providers.GlanceProvider.glance_client')
class ImageTest(unittest.TestCase):
    if sys.version_info.major >= 3:
        builtin_module = 'builtins'
    else:
        builtin_module = '__builtin__'

    def setUp(self):
        self.config = {
            'disk': {
                'image': {
                    'name': 'TestImageName',
                    'provider': 'see.image_providers.GlanceProvider',
                    'provider_configuration': {
                        'path': '/foo/bar',
                        'os_auth': {
                            'username': 'dummy',
                            'password': 'dmpwd'
                        }
                    }
                }
            }
        }

        self.wrongimage = mock.MagicMock()
        self.wrongimage.id = '1'
        self.wrongimage.name = 'NonRequestedTestImageName'
        self.wrongimage.updated_at = '2017-02-14T00:00:00Z'
        self.wrongimage.status = 'active'

        self.image1 = mock.MagicMock()
        self.image1.id = '1'
        self.image1.checksum = '1111'
        self.image1.name = 'TestImageName'
        self.image1.updated_at = u'2017-02-14T00:00:00Z'
        self.image1.status = 'active'

        self.image2 = mock.MagicMock()
        self.image2.id = '2'
        self.image2.checksum = '2222'
        self.image2.name = 'TestImageName'
        self.image2.updated_at = u'2017-02-15T00:00:00Z'
        self.image2.status = 'active'

        self.image3 = mock.MagicMock()
        self.image3.id = '3'
        self.image3.checksum = '3333'
        self.image3.name = 'TestImageName'
        self.image3.updated_at = u'2017-02-15T00:00:00Z'
        self.image3.status = 'queued'

    def test_fresh_image_exists(self, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1]

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 32503680000.0  # Jan 1st, 3000

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_not_called()

    def test_image_does_not_exist(self, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.wrongimage]

        os_mock.path.exists.return_value = False
        resources = Resources('foo', self.config)
        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    def test_image_unavailable_target_is_file(self, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = []

        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']
        assert resources.provider_image == expected_image_path

    def test_image_unavailable_target_is_dir(self, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image3]

        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.side_effect = [True, False, True]
        os_mock.path.isfile.return_value = False
        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/3'
        assert resources.provider_image == expected_image_path

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_image_unavailable_target_does_not_exist(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image2]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '2222'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.return_value = False
        os_mock.path.isfile.return_value = False
        os_mock.path.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/2'
        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('2')
        self.assertEqual([mock.call('/foo/bar/2.part', 'wb'),
                          mock.call('/foo/bar/2.part', 'rb')],
                         open_mock.call_args_list)
        os_mock.remove.assert_not_called()

    def test_image_unavailable_target_is_dir_no_cached(self, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image3]

        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname
        os_mock.path.exists.side_effect = lambda x: {'/foo/bar/1': False,
                                                     '/foo/bar/1.part': False,
                                                     '/foo/bar/3': False,
                                                     '/foo/bar/3.part': False,
                                                     '/foo/bar': True}[x]
        os_mock.path.isfile.return_value = False

        resources = Resources('foo', self.config)
        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_stale_image_exists(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1111'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, False, False]
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('1')
        self.assertEqual([mock.call('/foo/bar.part', 'wb'),
                          mock.call('/foo/bar.part', 'rb')],
                         open_mock.call_args_list)
        os_mock.remove.assert_not_called()

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_same_name_image_is_downloading_older_exists(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1, self.image2]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '2222'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, True]
        os_mock.path.isfile.return_value = False
        os_mock.path.dirname.return_value = '/foo/bar'

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1'

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_not_called()
        open_mock.assert_not_called()
        os_mock.remove.assert_not_called()

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_same_name_image_is_downloading_older_does_not_exist(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1, self.image2]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '2222'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, True, False, False]
        os_mock.path.isfile.return_value = False
        os_mock.path.dirname.return_value = '/foo/bar'

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1'

        with self.assertRaises(FileNotFoundError):
            assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_not_called()
        open_mock.assert_not_called()
        os_mock.remove.assert_not_called()

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_same_name_images_exist(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1, self.image2]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '2222'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, False, False]
        os_mock.path.isfile.return_value = False

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/2'

        assert resources.provider_image == expected_image_path
        glance_mock.images.data.assert_called_with('2')
        self.assertEqual([mock.call('/foo/bar/2.part', 'wb'),
                          mock.call('/foo/bar/2.part', 'rb')],
                         open_mock.call_args_list)
        os_mock.remove.assert_not_called()

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    def test_checksum_mismatch(self, hashlib_mock, open_mock, glance_mock, os_mock, _):
        glance_mock.images.list.return_value = [self.image1]

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1234'
        hashlib_mock.md5.return_value = md5

        os_mock.path.exists.side_effect = [True, False, False]
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 0

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']

        open_mock.reset_mock()
        with self.assertRaisesRegexp(RuntimeError, 'Checksum failure. File: '):
            assert resources.provider_image == expected_image_path

        glance_mock.images.data.assert_called_with('1')

        self.assertEqual([mock.call('/foo/bar.part', 'wb'),
                          mock.call('/foo/bar.part', 'rb')],
                         [call for call in open_mock.call_args_list if
                          call == mock.call('/foo/bar.part', 'wb') or
                          call == mock.call('/foo/bar.part', 'rb')])
        os_mock.remove.assert_called_once_with('/foo/bar.part')
