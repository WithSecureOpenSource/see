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

"""Module for tracing and analysing network activity of a running VM.

Tshark is required by both the acquisition and analysis Hooks.

https://www.wireshark.org

"""

import os
from see import Hook

from .utils import launch_process, collect_process_output, create_folder


TSHARK = 'tshark'


class NetworkTracerHook(Hook):
    """
    Network tracing hook.

    On the given starting event it starts dumping the Context's network traffic
    on a file in the given folder.

    configuration::

        {
          "results_folder": "/folder/where/to/store/pcap/file",
          "start_trace_on_event": "event_triggering_network_tracing",
          "stop_trace_on_event": "event_triggering_network_tracing_end",
          "trace_limit": 1024,
          "delete_trace_file": False
        }

    If trace_limit is given, the network capturing will stop
    once the given limit in KB is reached.

    If delete_trace_file is set to True, it will delete the trace file
    at the end of the execution. Default behaviour is to keep it.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.setup_handlers()
        self.pcap_path = None
        self.tracer_process = None

    def setup_handlers(self):
        if {'start_trace_on_event',
            'stop_trace_on_event'} <= set(self.configuration):
            self.context.subscribe(self.configuration['start_trace_on_event'],
                                   self.start_trace_handler)
            self.logger.debug("Network tracing start registered at %s event",
                              self.configuration['start_trace_on_event'])

            self.context.subscribe(self.configuration['stop_trace_on_event'],
                                   self.stop_trace_handler)
            self.logger.debug("Network tracing stop registered at %s event",
                              self.configuration['stop_trace_on_event'])

    def start_trace_handler(self, event):
        folder_path = self.configuration['results_folder']

        self.logger.debug("Event %s: starting network tracing.", event)

        create_folder(folder_path)
        self.pcap_path = os.path.join(folder_path, "%s.pcap" % self.identifier)

        command = [TSHARK, '-w', self.pcap_path,
                   '-i', self.context.network.bridgeName()]
        if 'trace_limit' in self.configuration:
            command.extend(
                ('-a', 'filesize:%d' % self.configuration['trace_limit']))

        self.tracer_process = launch_process(*command)
        self.context.trigger("network_tracing_started", path=self.pcap_path)

        self.logger.info("Network tracing started.")

    def stop_trace_handler(self, event):
        self.logger.debug("Event %s: stopping network tracing.", event)

        self.tracer_process.terminate()
        tshark_log = self.tracer_process.communicate()[0]
        self.logger.info("Network tracing stopped.")

        if not os.path.exists(self.pcap_path):
            raise RuntimeError("No pcap file was produced, thark log:\n%s"
                               % tshark_log)

    def cleanup(self):
        if self.configuration.get('delete_trace_file', False):
            if self.pcap_path is not None and os.path.exists(self.pcap_path):
                os.remove(self.pcap_path)


class NetworkAnalysisHook(Hook):
    """
    Network trace analiser.

    On the given event it analyses the network trace via TShark.

    configuration::

        {
          "results_folder": "/folder/where/to/store/pcap/file",
          "start_processing_on_event": "event_triggering_processing",
          "wait_processing_on_event": "event_waiting_processing",
          "log_format": "fields|pdml|ps|psml|text",
        }

    The processing is carried on concurrently,
    therefore the wait_processing_on_event is used to wait for the results.

    The log_format field allows to choose TShark output format.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.setup_handlers()
        self.pcap_path = None
        self.analysis_process = None

    def setup_handlers(self):
        self.context.subscribe('network_tracing_started',
                               self.network_trace_handler)

        if {'start_processing_on_event',
            'wait_processing_on_event'} <= set(self.configuration):
            self.context.subscribe(
                self.configuration['start_processing_on_event'],
                self.start_processing_handler)
            self.context.subscribe(
                self.configuration['wait_processing_on_event'],
                self.stop_processing_handler)

    def network_trace_handler(self, event):
        if hasattr(event, 'path'):
            self.logger.debug("Event %s: new network trace %s.",
                              event, event.path)
            self.pcap_path = event.path
        else:
            self.logging.warning("%s event received, no path specified.")

    def start_processing_handler(self, event):
        self.logger.debug("Event %s: start analysis of %s.",
                          event, self.pcap_path)
        self.analysis_process = launch_process(
            TSHARK, '-r', self.pcap_path,
            '-T', self.configuration.get('log_format', 'text'))

    def stop_processing_handler(self, event):
        log_path = os.path.join(self.configuration['results_folder'],
                                "network.log")

        self.logger.debug("Event %s: waiting Pcap analysis.", event)

        collect_process_output(self.analysis_process, log_path)
