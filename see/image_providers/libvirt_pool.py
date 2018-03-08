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
"""LibVirt storage pool image provider.

This provider retrieves the path of an image within a libvirt storage pool.
If the path is not within a storage pool a new one will be created.

provider_parameters:
    hypervisor (str): Connection URL to the libvirt hypervisor. Default 'qemu:///system'
    storage_pool_path (str): Absolute path to the libvirt storage pool. Only dir type pools are supported.

"""

import libvirt
import os

from see.interfaces import ImageProvider

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

POOL_CONFIG_XML = """
<pool type='dir'>
  <name>{0}</name>
  <target>
    <path>{0}</path>
  </target>
</pool>
"""


class LibvirtPoolProvider(ImageProvider):

    def __init__(self, parameters):
        super(LibvirtPoolProvider, self).__init__(parameters)

    @property
    def image(self):
        path = "%s/%s" % (self.configuration.get(
            'storage_pool_path').rstrip('/'), self.uri.lstrip('/'))

        if not os.path.exists(path):
            raise FileNotFoundError(path)

        hypervisor = libvirt.open(
            self.configuration.get('hypervisor', 'qemu:///system'))

        try:
            volume = hypervisor.storageVolLookupByPath(path)
            return volume.path()
        except libvirt.libvirtError:
            pool = hypervisor.storagePoolDefineXML(POOL_CONFIG_XML.format(
                self.configuration.get('storage_pool_path')))
            pool.setAutostart(True)
            pool.create()
            pool.refresh()
            return pool.storageVolLookupByName(self.uri).path()
