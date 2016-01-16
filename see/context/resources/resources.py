# Copyright 2015-2016 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""SEE's resources interface contract.

To expand SEE's hypervisor support, the developer must adhere to the following interface.

"""

import logging


class Resources(object):
    """Resources Class interface."""
    def __init__(self, identifier, configuration):
        self.identifier = identifier
        self.configuration = configuration
        self.logger = logging.getLogger(identifier)

    @property
    def hypervisor(self):
        """Hypervisor connection getter.

        Once called this property must return an object of type libvirt.virConnect
        connected to the type of hypervisor in which the Domain is running.

        This property must be provided.

        """
        raise NotImplementedError("Hypervisor connection not provided.")

    @property
    def domain(self):
        """Domain Object getter.

        Once called this property must return an object of type libvirt.virDomain
        representing the Domain which is intended to be controlled.

        This property must be provided.

        """
        raise NotImplementedError("Domain not provided.")

    @property
    def network(self):
        """Network Object getter.

        Once called this property must return an object of type libvirt.virNetwork
        representing the Network which is intended to be controlled.

        """
        raise NotImplementedError("Network not provided.")

    @property
    def storage_pool(self):
        """Storage Pool Object getter.

        Once called this property must return an object of type libvirt.virStoragePool
        representing the Storage Pool which is intended to be controlled.

        """

        raise NotImplementedError("Storage Pool not provided.")

    def cleanup(self):
        """Resources cleanup routine.

        This method is called once the Environment has ended, therefore it must ensure
        that no allocated libvirt resource is left behind.

        This method must be provided.

        """
        raise NotImplementedError("Storage Pool not provided.")
