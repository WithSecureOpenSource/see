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

import json
import uuid
import logging

from see.hooks import hooks_factory


class Environment(object):
    """
    SEE Environment.

    Given a context factory and the list of the Hooks,
    it sets them up accordingly.

    The Hooks configuration consist in a dictionary or a path to a JSON file.
    The Hooks configuration accepts two fields::
      * configuration: a set of values which will be propagated to all Hooks.
      * hooks: a list of elements containing the instruction for each Hook.
        Each element must contain two fields:
          * name: fully qualified Python name of the Hook class.
          * configuration: configuration values specific to the Hook.
            Any value colliding with the generic configuration
            will overwrite it.

    @param contextfactory: (callable) must return a functional Context object.
    @param configuration: (str|dict) Hooks configuration,
      must be either a dictionary or a path to a JSON file.
    @param identifier: (str) UUID of the Environment,
      a random one will be assigned if not provided.
    @param logger: (logging.Logger) logger object, if not given,
      a default one will be created.

    """
    def __init__(self, contextfactory, configuration,
                 identifier=None, logger=None):
        self._identifier = identifier or str(uuid.uuid4())
        self._context = None
        self._hookmanager = None
        self._contextfactory = contextfactory
        self.configuration = configuration
        self.logger = logger or logging.getLogger(
            "%s.%s" % (self.__module__, self.__class__.__name__))

    def __enter__(self):
        self.allocate()
        return self

    def __exit__(self, *args):
        self.deallocate()

    @property
    def identifier(self):
        return self._identifier

    @property
    def context(self):
        """Returns the Context if allocated, RuntimeError is raised if not."""
        if self._context is not None:
            return self._context
        else:
            raise RuntimeError('Environment not allocated')

    def allocate(self):
        """Builds the context and the Hooks."""
        self.logger.debug("Allocating environment.")
        self._allocate()
        self.logger.debug("Environment successfully allocated.")

    def _allocate(self):
        self.configuration = load_configuration(self.configuration)
        self._context = self._contextfactory(self.identifier)
        self._hookmanager = hooks_factory(self.identifier,
                                          self.configuration,
                                          self._context)

    def deallocate(self):
        """Cleans up the context and the Hooks."""
        self.logger.debug("Deallocating environment.")
        self._deallocate()
        self.logger.debug("Environment successfully deallocated.")

    def _deallocate(self):
        cleanup(self.logger, self._hookmanager, self._context)
        self._context = None
        self._hookmanager = None


def load_configuration(configuration):
    """Returns a dictionary, accepts a dictionary or a path to a JSON file."""
    if isinstance(configuration, dict):
        return configuration
    else:
        with open(configuration) as configfile:
            return json.load(configfile)


def cleanup(logger, *args):
    """Environment's cleanup routine."""
    for obj in args:
        if obj is not None and hasattr(obj, 'cleanup'):
            try:
                obj.cleanup()
            except NotImplementedError:
                pass
            except Exception:
                logger.exception("Unable to cleanup %s object", obj)
