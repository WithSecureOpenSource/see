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
"""Glance image provider.

This provider retrieves the requested image from an OpenStack Glance service if
it doesn't already exist on the configured target path. Images can be requested
by name or UUID; if name is requested the latest matching image is retrieved.

provider_parameters:
    target_path (str): Absolute path where to download the image. If target_path
                       is a directory, the image's UUID will be used as filename.
    glance_url (str):  The URL of the OpenStack Glance service to query for the
                       images.
    os_auth (dict):    A dictionary with OpenStack authentication parameters as
                       needed by OpenStack's Keystone client.

"""

import os
import hashlib
import tempfile

from datetime import datetime
from see.interfaces import ImageProvider

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def verify_checksum(path, checksum):
    hash_md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hash_md5.update(chunk)
    return hash_md5.hexdigest() == checksum


class GlanceProvider(ImageProvider):

    def __init__(self, parameters):
        super(GlanceProvider, self).__init__(parameters)
        self._keystone_client = None
        self._glance_client = None

    @property
    def image(self):
        try:
            metadata = self._retrieve_metadata()
        except FileNotFoundError:
            if os.path.exists(self.configuration['target_path']):
                if os.path.isfile(os.path.realpath(
                        self.configuration['target_path'])):
                    return self.configuration['target_path']
                else:
                    for image in self._find_potentials():
                        tgt = os.path.join(self.configuration['target_path'],
                                           image.id)
                        if os.path.exists(tgt):
                            return tgt
            raise

        if (os.path.exists(self.configuration['target_path']) and
            os.path.isfile(os.path.realpath(
                self.configuration['target_path'])) and
            datetime.fromtimestamp(os.path.getmtime(
                self.configuration['target_path'])) >
                datetime.strptime(metadata.updated_at, "%Y-%m-%dT%H:%M:%SZ")):
            return self.configuration['target_path']

        target = ('/'.join((self.configuration['target_path'].rstrip('/'),
                            metadata.id))
                  if os.path.isdir(self.configuration['target_path'])
                  else self.configuration['target_path'])
        self._download_image(metadata, target)
        return target

    @property
    def _token(self):
        self.keystone_client.authenticate()
        return self.keystone_client.get_token(self.keystone_client.session)

    @property
    def keystone_client(self):
        if self._keystone_client is None:
            from keystoneclient.client import Client as Kclient
            self._keystone_client = Kclient(self.configuration['os_auth'])
        return self._keystone_client

    @property
    def glance_client(self):
        if self._glance_client is None:
            from glanceclient.v2.client import Client as Gclient
            self._glance_client = Gclient(
                self.configuration['glance_url'], token=self._token)
        return self._glance_client

    def _find_potentials(self):
        return sorted([image for image in self.glance_client.images.list()
                       if (image.id == self.uri or image.name == self.uri)
                       and image.status != 'active'],
                      key=lambda x: x.updated_at, reverse=True)

    def _retrieve_metadata(self):
        try:
            return sorted([image for image in self.glance_client.images.list()
                           if (image.id == self.uri or image.name == self.uri)
                           and image.status == 'active'],
                          key=lambda x: x.updated_at, reverse=True)[0]
        except IndexError:
            raise FileNotFoundError(self.uri)

    def _download_image(self, img_metadata, target):
        img_downloader = self.glance_client.images.data(img_metadata.id)
        _, temp = tempfile.mkstemp(dir=os.path.dirname(target), suffix='.part')
        with open(temp, 'wb') as imagefile:
            for chunk in img_downloader:
                imagefile.write(chunk)
        if not verify_checksum(temp, img_metadata.checksum):
            os.remove(temp)
            raise RuntimeError('Checksum failure. File: %s' % target)
        os.rename(temp, target)