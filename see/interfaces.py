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

import logging

from see.observer import Observable, Observer


class Context(Observable):
    """Abstract base class for the Context."""
    def __init__(self, identifier):
        super(Context, self).__init__(identifier)

    def cleanup(self):
        raise NotImplementedError("Not implemented")


class Hook(Observer):
    """Abstract base class for the Hooks."""
    def __init__(self, parameters):
        super(Hook, self).__init__(parameters.identifier, parameters.context)
        self.configuration = parameters.configuration
        self.logger = logging.getLogger(
            '%s.%s' % (self.__module__, self.__class__.__name__))

    def cleanup(self):
        raise NotImplementedError("Not implemented")


class ImageProvider(object):
    """Abstract base class for image provider backends."""
    def __init__(self, parameters):
        super(ImageProvider, self).__init__()
        self.configuration = parameters.get('provider_configuration')
        self.uri = parameters.get('uri')
        self.logger = logging.getLogger(
            '%s.%s' % (self.__module__, self.__class__.__name__))

    @property
    def image(self):
        raise NotImplementedError("Not implemented")
