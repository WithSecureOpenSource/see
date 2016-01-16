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

"""Module for triggering time based events."""

from threading import Timer

from see import Hook


class TimersHook(Hook):
    """
    Timers hook.

    Allows to trigger events at given times.

    configuration::

        {
          "timers": {40: "event_to_trigger_after_40_seconds"}
        }

    Timers are started during Hook's initialization.

    """
    def __init__(self, parameters):
        super().__init__(parameters)

        for time, event in self.configuration.get('timers', {}).items():
            Timer(time, self.context.trigger, args=(event, )).start()
