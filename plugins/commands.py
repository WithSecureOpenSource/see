# Copyright 2016 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""Module for executing commands within the guest OS.

It depends on Requests library.

https://pypi.python.org/pypi/requests

The Agent at see/plugins/agent.py must be installed and executed
within the guest OS.

"""

import os
import json
import requests

from see import Hook


class CommandsHook(Hook):
    """
    Commands execution Hook.

    Reacts to Events sending commands to the Guest Agent.

    * Event("run_command", async=False, command="ls -al")
        Executes a simple command within the Guest OS via the Agent.
        Blocks until the results are not delivered and logs them.

    * Event("run_sample", async=True, sample="/local/path/file.exe",
            command="start {sample}")
        Uploads a sample and executes a command. The keyword {sample}
        within the command will be expanded with the path of the uploaded
        file on the Guest. The action does not wait for the results
        as the async flag is set.

    configuration::

        {
          "agent-host": "IP address of the Agent running within the Guest",
          "agent-port": 8080,
        }

    The IP address of the Agent can be, as well, communicated via an Event
    'ip_address' within the field 'address'.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.setup_handlers()
        self.host = self.configuration.get('agent-host')
        self.port = self.configuration['agent-port']

    def setup_handlers(self):
        self.context.subscribe('ip_address', self.set_address_handler)
        self.context.subscribe('run_command', self.run_command_handler)
        self.context.subscribe('run_sample', self.run_sample_handler)

        self.logger.debug("Command execution registered at run_command event")
        self.logger.debug("Sample execution registered at run_sample event")

    def set_address_handler(self, event):
        self.logger.debug("Event %s: agent address <%s>.",
                          event, event.address)

        self.host = event.address

    def run_command_handler(self, event):
        self.logger.debug("Event %s: running command <%s>.",
                          event, event.command)

        async = hasattr(event, 'async') and event.async or False
        response = self.command_request(event.command, async)

        self.log_command_response(event.command, response, async)

    def run_sample_handler(self, event):
        self.logger.debug("Event %s: running command <%s>.",
                          event, event.command)

        async = hasattr(event, 'async') and event.async or False
        response = self.sample_request(event.command, event.sample, async)

        self.log_command_response(event.command, response, async)

    def command_request(self, command, async):
        url = 'http://%s:%d' % (self.host, self.port)
        response = requests.get(url, params={'command': command,
                                             'async': int(async)})
        response.raise_for_status()

        return response

    def sample_request(self, command, sample, async):
        url = 'http://%s:%d' % (self.host, self.port)
        files = {'file': open(sample, 'rb')}
        response = requests.post(url, files=files,
                                 params={'command': command,
                                         'sample': os.path.basename(sample),
                                         'async': int(async)})
        response.raise_for_status()

        return response

    def log_command_response(self, command, response, async):
        if not async:
            results = response.json()

            self.logger.info("Command <%s> output:\n%s",
                             command, json.dumps(results, indent=2))
        else:
            self.logger.info("Asynchronous command <%s> dispatched to agent.",
                             command)
