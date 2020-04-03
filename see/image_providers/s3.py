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
"""S3 image provider.

This provider retrieves the requested image from an S3-compatible endpoint if
it doesn't alread exist on the configured target path or if the existing local
image is older than it's remote S3 counterpart.

provider_parameters:
    bucket_name (str):      Name of the S3 bucket where the image is stored.
    name (str):             Key of the image in S3.
    path (str):             Absolute path where to download the image.
                            If target_path is an existing file, it will be
                            overwritten if the remote image is newer. Otherwise
                            target_path is understood to be a directory.
    auth (dict):            A dictionary with S3 authentication parameters as
                            needed by boto3's Session.resource class, see
                            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html#boto3.session.Session.resource
    libvirt_pool (dict):    An optional dictionary with backing libvirt pool
                            configuration, with the following keys:
        hypervisor (str):   The URL of the hypervisor to connect to.
        name (str):         The name of the libvirt storage pool.
"""

import os
import boto3

from datetime import datetime
from botocore.exceptions import ClientError
from see.interfaces import ImageProvider
from see.image_providers.helpers import verify_etag

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class S3Provider(ImageProvider):

    def __init__(self, parameters):
        super(S3Provider, self).__init__(parameters)
        self._s3_client = None

    @property
    def image(self):
        metadata = self.s3_client.ObjectSummary(
            self.configuration['bucket_name'], self.name)
        try:
            if (os.path.exists(self.configuration['path']) and
                    os.path.isfile(os.path.realpath(
                        self.configuration['path'])) and
                    datetime.fromtimestamp(os.path.getmtime(
                        self.configuration['path'])) > metadata.last_modified):
                return self.configuration['path']
        except ClientError:
            if os.path.exists(self.configuration['path']) and os.path.isfile(
                    os.path.realpath(self.configuration['path'])):
                return self.configuration['path']
            raise FileNotFoundError('No image found')

        target = (self.configuration['path']
                  if os.path.isfile(self.configuration['path'])
                  else os.path.join(self.configuration['path'],
                                    metadata.e_tag.strip('"')))

        os.makedirs(os.path.dirname(os.path.realpath(target)), exist_ok=True)

        return self._download_image(metadata, target)

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.resource('s3',
                                             **self.configuration.get('auth'))
        return self._s3_client

    def _download_image(self, metadata, target):
        def _older_image():
            for version in sorted(
                    self.s3_client.meta.client.list_object_versions(
                        Bucket=self.configuration['bucket_name'],
                        Prefix=self.name)['Versions'],
                    key=lambda v: v['LastModified'], reverse=True):
                oldimg = os.path.join(os.path.dirname(target),
                                      version['ETag'].strip('"'))
                if os.path.exists(oldimg) and oldimg != target:
                    return oldimg
            raise FileNotFoundError('No viable images available')

        partfile = '{}.part'.format(target)
        if os.path.exists(partfile):
            return _older_image()

        if not os.path.exists(target):
            try:
                self.s3_client.Object(self.configuration['bucket_name'],
                                      self.name).download_file(partfile)
            except ClientError:
                raise FileNotFoundError('No image found')

            if not verify_etag(partfile, metadata.e_tag.strip('"')):
                os.remove(partfile)
                raise RuntimeError('Checksum failure. File: %s' % target)
            os.rename(partfile, target)

            if self.configuration.get('libvirt_pool'):
                import libvirt
                hypervisor = libvirt.open(
                    self.configuration['libvirt_pool'].get('hypervisor',
                                                           'qemu:///system'))
                pool = hypervisor.storagePoolLookupByName(
                    self.configuration['libvirt_pool']['name'])
                pool.refresh()
        return target
