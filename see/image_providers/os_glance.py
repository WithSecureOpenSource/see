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
    name (str):          Name of the image to download.
    path (str):          Absolute path where to download the image.
                         If target_path is an existing file, it will be
                         overwritten if the image is newer. Otherwise
                         target_path is understood to be a directory and the
                         image's UUID will be used as filename.
    os_auth (dict):      A dictionary with OpenStack authentication parameters
                         as needed by OpenStack's Keystone client.
    session (dict):      A dictionary with OpenStack Session parameters. Allows
                         authentication to Keystone over TLS.
    libvirt_pool (dict): An optional dictionary with backing libvirt pool
                         configuration, with the following keys:
        hypervisor (str):   The URL of the hypervisor to connect to.
        name (str):         The name of the libvirt storage pool.
"""

import os

from datetime import datetime
from see.interfaces import ImageProvider
from see.image_providers.helpers import verify_checksum

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class GlanceProvider(ImageProvider):

    def __init__(self, parameters):
        super(GlanceProvider, self).__init__(parameters)
        self._os_session = None
        self._glance_client = None

    @property
    def image(self):
        try:
            metadata = self._retrieve_metadata()
        except FileNotFoundError:
            if os.path.exists(self.configuration['path']):
                if os.path.isfile(os.path.realpath(self.configuration['path'])):
                    return self.configuration['path']
                else:
                    for image in self._find_potentials():
                        tgt = os.path.join(self.configuration['path'], image.id)
                        if os.path.exists(tgt):
                            return tgt
            raise

        if (os.path.exists(self.configuration['path']) and
                os.path.isfile(os.path.realpath(
                    self.configuration['path'])) and
                datetime.fromtimestamp(os.path.getmtime(
                    self.configuration['path'])) >
                datetime.strptime(metadata.updated_at, "%Y-%m-%dT%H:%M:%SZ")):
            return self.configuration['path']

        target = (self.configuration['path']
                  if os.path.isfile(self.configuration['path'])
                  else os.path.join(self.configuration['path'], metadata.id))

        os.makedirs(os.path.dirname(os.path.realpath(target)), exist_ok=True)

        return self._download_image(metadata, target)

    @property
    def os_session(self):
        if self._os_session is None:
            from keystoneauth1.identity import v3
            from keystoneauth1.session import Session

            self._os_session = Session(
                auth=v3.Password(**self.configuration['os_auth']),
                verify=self.configuration['session'].get('cacert', False),
                cert=self.configuration['session'].get('cert'))
        return self._os_session

    @property
    def glance_client(self):
        if self._glance_client is None:
            from glanceclient.v2.client import Client as Gclient
            self._glance_client = Gclient(session=self.os_session)
        return self._glance_client

    def _find_potentials(self):
        return sorted(
            [image for image in self.glance_client.images.list(
                filters={'name': self.name})
             if image.status != 'active'],
            key=lambda x: x.updated_at, reverse=True)

    def _retrieve_metadata(self):
        try:
            return sorted([image for image in self.glance_client.images.list(
                filters={'name': self.name, 'status': 'active'})],
                          key=lambda x: x.updated_at, reverse=True)[0]
        except IndexError:
            raise FileNotFoundError(self.name)

    def _download_image(self, img_metadata, target):
        def _older_image():
            for image in sorted(
                    [image for image in self.glance_client.images.list(
                        filters={'name': self.name})
                     if image.status in ('active', 'deactivated')],
                    key=lambda x: x.updated_at, reverse=True):
                newtarget = os.path.join(os.path.dirname(target), image.id)
                if os.path.exists(newtarget):
                    return newtarget
            raise FileNotFoundError('No viable images available')

        partfile = '{}.part'.format(target)
        if os.path.exists(partfile):
            return _older_image()
        if not os.path.exists(target):
            img_downloader = self.glance_client.images.data(img_metadata.id)
            with open(partfile, 'wb') as imagefile:
                for chunk in img_downloader:
                    imagefile.write(chunk)
            if not verify_checksum(partfile, img_metadata.checksum):
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
