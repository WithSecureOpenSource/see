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

"""Module for acquiring screenshots of a running VM."""

import os
from io import BytesIO

from see import Hook
from see.context import RUNNING, PAUSED

from .utils import create_folder


class ScreenHook(Hook):
    """
    Screenshot capturing hook.

    On the given event, it captures the Context's screen state
    on a file in the given folder.

    configuration::

        {
          "results_folder": "/folder/where/to/store/memory/dump/file"
          "screenshot_on_event": ["event_triggering_memory_dump"]
        }

    The "screenshot_on_event" can be either a string representing the event
    or a list of multiple ones.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.setup_handlers()

    def setup_handlers(self):
        screenshots = self.configuration.get('screenshot_on_event', ())
        events = isinstance(screenshots, str) and [screenshots] or screenshots

        for event in events:
            self.context.subscribe(event, self.screenshot_handler)
            self.logger.debug("Screenshot registered at %s event", event)

    def screenshot_handler(self, event):
        self.logger.debug("Event %s: capturing screenshot.", event)

        screenshot_path = self.screenshot(event)

        self.logger.info("Screenshot %s captured.", screenshot_path)

    def screenshot(self, event):
        self.assert_context_state()

        folder_path = self.configuration['results_folder']
        screenshot_path = os.path.join(folder_path,
                                       "%s_%s.ppm" % (self.identifier, event))
        create_folder(folder_path)

        with open(screenshot_path, 'wb') as screenshot_file:
            screenshot_stream = screenshot(self.context)
            screenshot_file.write(screenshot_stream)

    def assert_context_state(self):
        if self.context.domain.state()[0] not in (RUNNING, PAUSED):
            raise RuntimeError("Context must be running or paused")


def screenshot(context):
    """Takes a screenshot of the vnc connection of the guest.
    The resulting image file will be in Portable Pixmap format (PPM).

    @param context: (see.Context) context of the Environment.
    @return: (str) binary stream containing the screenshot.

    """
    handler = lambda _, buff, file_handler: file_handler.write(buff)

    string = BytesIO()
    stream = context.domain.connect().newStream(0)
    context.domain.screenshot(stream, 0, 0)
    stream.recvAll(handler, string)

    return string.getvalue()
