import os
import sys
import mock
import unittest

from datetime import datetime
from botocore.exceptions import ClientError
from see.context.resources.resources import Resources

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

if sys.version_info.major < 3:
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


@mock.patch('see.image_providers.s3.os')
@mock.patch('see.image_providers.S3Provider.s3_client')
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
                    'provider': 'see.image_providers.S3Provider',
                    'provider_configuration': {
                        'bucket_name': 'TestBucketName',
                        'path': '/foo/bar',
                        'auth': {
                            'aws_access_key_id': 'NoAccessKey',
                            'aws_secret_access_key': 'NoSecretAccessKey',
                            'aws_session_token': 'NoToken'
                        }
                    }
                }
            }
        }

        self.wrongimage = mock.MagicMock()
        self.wrongimage.name = 'NonRequestedTestImageName'
        self.wrongimage.last_modified = datetime(2020, 1, 15, 0, 0, 0)

        self.image1 = mock.MagicMock()
        self.image1.name = 'TestImageName'
        self.image1.last_modified = datetime(2020, 1, 15, 0, 0, 0)
        self.image1.e_tag = '1111'

    def test_fresh_image_exists(self, s3_mock, os_mock):
        """The image exists on the local filesystem and is newer than the remote."""
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 32503680000.0  # Jan 1st, 3000

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']

        assert resources.provider_image == expected_image_path
        s3_mock.Object.download_file.assert_not_called()

    @mock.patch('see.image_providers.helpers.os')
    def test_image_does_not_exist(self, _, s3_mock, os_mock):
        """The image is unavailable locally or remotely."""
        s3_mock.reset_mock()
        s3_mock.Object.download_file.side_effect = ClientError({}, 'MockOperation')

        os_mock.path.exists.return_value = False
        os_mock.path.isfile.return_value = True
        resources = Resources('foo', self.config)

        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image

    def test_image_unavailable_target_is_file(self, s3_mock, os_mock):
        """The image is unavailable remotely but there's a local copy."""
        summary = mock.MagicMock()
        type(summary).last_modified = mock.PropertyMock(side_effect=ClientError({}, 'MockOperation'))
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = summary

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        os_mock.path.getmtime.return_value = 32503680000.0  # Jan 1st, 3000

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path']
        assert resources.provider_image == expected_image_path
        s3_mock.Object.download_file.assert_not_called()

    def test_image_unavailable_target_is_dir(self, s3_mock, os_mock):
        """The image is unavailable remotely but there's a local copy in the configured target directory."""
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1

        os_mock.path.isfile.return_value = False
        os_mock.path.join = os.path.join
        os_mock.path.exists.side_effect = [True, False, True]

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1111'
        assert resources.provider_image == expected_image_path

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    @mock.patch('see.image_providers.helpers.os')
    def test_image_unavailable_target_does_not_exist(self, _hom, hashlib_mock, _, s3_mock, os_mock):
        """The image is not available locally, download from remote."""
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        downloader = mock.MagicMock()
        s3_mock.Object.return_value = downloader

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1111'
        hashlib_mock.md5.return_value = md5

        os_mock.path.exists.return_value = False
        os_mock.path.isfile.return_value = False
        os_mock.path.getmtime.return_value = 0
        os_mock.path.join = os.path.join

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1111'
        assert resources.provider_image == expected_image_path
        s3_mock.Object.assert_called_with(self.config['disk']['image']['provider_configuration']['bucket_name'],
                                          self.config['disk']['image']['name'])
        downloader.download_file.assert_called_with(expected_image_path + '.part')
        os_mock.rename.assert_called_once_with(expected_image_path + '.part', expected_image_path)

    def test_image_unavailable_target_is_dir_no_cached(self, s3_mock, os_mock):
        """The image is not available remotely or in the configured target directory."""
        os_mock.path.exists.side_effect = [True, False, False]
        os_mock.path.isfile.return_value = False
        os_mock.path.join = os.path.join

        downloader = mock.MagicMock()
        downloader.download_file.side_effect = ClientError({}, 'MockOperation')
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        s3_mock.Object.return_value = downloader

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1111'
        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image
        s3_mock.Object.assert_called_with(self.config['disk']['image']['provider_configuration']['bucket_name'],
                                          self.config['disk']['image']['name'])
        downloader.download_file.assert_called_with(expected_image_path + '.part')

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    @mock.patch('see.image_providers.helpers.os')
    def test_stale_image_exists(self, _hom, hashlib_mock, _, s3_mock, os_mock):
        """A local image exists but it is older than the remote image."""
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        downloader = mock.MagicMock()
        s3_mock.Object.return_value = downloader

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
        s3_mock.Object.assert_called_with(self.config['disk']['image']['provider_configuration']['bucket_name'],
                                          self.config['disk']['image']['name'])
        downloader.download_file.assert_called_with(expected_image_path + '.part')

    def test_same_name_image_is_downloading_older_exists(self, s3_mock, os_mock):
        """There is an ongoing download for the requested image but there is an older version on disk."""
        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = False
        os_mock.path.getmtime.return_value = 0
        os_mock.path.join = os.path.join
        os_mock.path.dirname = os.path.dirname

        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        s3_mock.meta.client.list_object_versions.return_value = {'Versions': [{'ETag': '0000', 'LastModified': datetime(2020, 1, 1)}]}
        downloader = mock.MagicMock()
        s3_mock.Object.return_value = downloader

        resources = Resources('foo', self.config)
        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/0000'

        assert resources.provider_image == expected_image_path
        s3_mock.Object.assert_not_called()
        downloader.download_file.assert_not_called()

    def test_same_name_image_is_downloading_older_does_not_exist(self, s3_mock, os_mock):
        """There is an ongoing download for the requested image and there is no older version on disk."""
        os_mock.path.exists.side_effect = [True, True, False]
        os_mock.path.isfile.return_value = False
        os_mock.path.join = os.path.join

        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        s3_mock.meta.client.list_object_versions.return_value = {'Versions': []}
        downloader = mock.MagicMock()
        s3_mock.Object.return_value = downloader

        resources = Resources('foo', self.config)

        with self.assertRaises(FileNotFoundError):
            _ = resources.provider_image
        s3_mock.Object.assert_not_called()
        downloader.download_file.assert_not_called()

    @mock.patch('%s.open' % builtin_module, new_callable=mock.mock_open)
    @mock.patch('see.image_providers.helpers.hashlib')
    @mock.patch('see.image_providers.helpers.os')
    def test_checksum_mismatch(self, _hom, hashlib_mock, _, s3_mock, os_mock):
        """The local image does not exist and the checksum of the downloaede image does not match."""
        s3_mock.reset_mock()
        s3_mock.ObjectSummary.return_value = self.image1
        downloader = mock.MagicMock()
        s3_mock.Object.return_value = downloader

        md5 = mock.MagicMock()
        md5.hexdigest.return_value = '1234'
        hashlib_mock.md5.return_value = md5

        os_mock.path.join = os.path.join
        os_mock.path.exists.return_value = False
        os_mock.path.isfile.return_value = False

        resources = Resources('foo', self.config)

        with self.assertRaisesRegex(RuntimeError, 'Checksum failure. File: '):
            _ = resources.provider_image

        expected_image_path = self.config['disk']['image']['provider_configuration']['path'] + '/1111'
        s3_mock.Object.assert_called_with(self.config['disk']['image']['provider_configuration']['bucket_name'],
                                          self.config['disk']['image']['name'])
        downloader.download_file.assert_called_with(expected_image_path + '.part')
        os_mock.remove.assert_called_once_with(expected_image_path + '.part')
