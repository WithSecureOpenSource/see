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

"""Module for acquiring and analysing memory snapshots of a running VM.

The VolatilityHook for analysing memory snapshots requires volatility.

http://www.volatilityfoundation.org

"""

import os
import libvirt
from threading import Event
from datetime import datetime

from see import Hook
from see.context import PAUSED

from .utils import launch_process, collect_process_output, create_folder


class MemoryHook(Hook):
    """
    Memory snapshotting hook.

    On the given event, it dumps the Context's memory state
    on a file in the given folder.

    configuration::

        {
          "results_folder": "/folder/where/to/store/memory/dump/file",
          "memory_snapshots_on_event": ["event_triggering_memory_snapshot"],
          "compress_snapshots": False,
          "delete_snapshots": False
        }

    "memory_snapshot_on_event" can be either a string or a list of Events.

    If "compress_snapshots" is set to True, the snapshot files will be
    archived as zlib to save space. Default to False.

    If "delete_snapshots" is set to True, the snapshot files will be deleted
    at the end of the execution. Default to False.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.memdumps = []
        self.setup_handlers()

    def setup_handlers(self):
        snapshots = self.configuration.get('memory_snapshots_on_event', ())
        events = isinstance(snapshots, str) and [snapshots] or snapshots

        for event in events:
            self.context.subscribe(event, self.snapshot_handler)
            self.logger.debug("Memory snapshot registered at %s event", event)

    def snapshot_handler(self, event):
        self.logger.debug("Event %s: taking memory snapshot.", event)

        snapshot_path = self.memory_snapshot(event)
        self.context.trigger("memory_snapshot_taken", path=snapshot_path)

        self.logger.info("Memory snapshot %s taken.", snapshot_path)

    def memory_snapshot(self, event):
        folder_path = self.configuration['results_folder']
        file_name = "%s_%s.bin%s" % (
            event,
            datetime.now().replace(microsecond=0).time().strftime("%H%M%S"),
            self.configuration.get('compress_snapshots', False)
            and '.gz' or '')
        snapshot_path = os.path.join(folder_path, file_name)

        create_folder(folder_path)
        self.dump_memory(snapshot_path)

        return snapshot_path

    def dump_memory(self, memory_dump_path):
        self.assert_context_state()
        memory_snapshot(self.context, memory_dump_path,
                        self.configuration.get('compress_snapshots', False))

        self.memdumps.append(memory_dump_path)

    def assert_context_state(self):
        if self.context.domain.state()[0] is not PAUSED:
            raise RuntimeError("Context must be paused during memory snapshot")

    def cleanup(self):
        if self.configuration.get('delete_snapshots', False):
            for memdump in self.memdumps:
                os.remove(memdump)


class VolatilityHook(Hook):
    """
    Volatility post-processor hook.

    On the given event, it runs the given Volatility plugins
    on all the provided memory snapshots.

    The memory snapshots files paths must be communicated through
    a "memory_snapsho_ttaken" event within the path attribute.

    configuration::

        {
          "results_folder": "/folder/where/to/store/memory/dump/file",
          "start_processing_on_event": "event_starting_async_processing",
          "wait_processing_on_event": "event_waiting_async_processing",
          "profile": "Win7SP1x64",
          "plugins": ["mutantscan"]
        }

    On start_processing_on_event, the volatility process will be started
    with the given plugins. All provided memory snapshots will be analysed
    sequentially.
    wait_processing_on_event allows to wait for the asyncronous processes
    to terminate.

    A profile key must be provided with the memory profile of the Sandbox.
    The list of plugins will be passed directly to Volatiliti's multiscan
    command.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.snapshots = []
        self.setup_handlers()
        self.processing_done = Event()

    def setup_handlers(self):
        self.context.subscribe('memory_snapshot_taken',
                               self.memory_snapshot_handler)

        if {'start_processing_on_event',
            'wait_processing_on_event'} <= set(self.configuration):
            event = self.configuration['start_processing_on_event']
            self.context.subscribe_async(event, self.start_processing_handler)
            self.logger.debug("Volatility scheduled at %s event", event)

            event = self.configuration['wait_processing_on_event']
            self.context.subscribe(event, self.stop_processing_handler)
            self.logger.debug("Volatility processing wait at %s event", event)

    def memory_snapshot_handler(self, event):
        if hasattr(event, 'path'):
            self.logger.debug("Event %s: new memory dump %s.",
                              event, event.path)
            self.snapshots.append(event.path)
        else:
            self.logging.warning("%s event received, no path specified.")

    def start_processing_handler(self, event):
        """Asynchronous handler starting the Volatility processes."""
        self.logger.debug("Event %s: starting Volatility process(es).", event)

        for snapshot in self.snapshots:
            self.process_snapshot(snapshot)

        self.processing_done.set()

    def process_snapshot(self, snapshot):
        profile = self.configuration.get('profile', ())

        for plugin in self.configuration.get('plugins', ()):
            try:
                process_memory_snapshot(snapshot, profile, plugin)
            except RuntimeError:
                self.logger.exception("Unable to run %s plugin.", plugin)

    def stop_processing_handler(self, event):
        self.logger.debug("Event %s: waiting for Volatility process(es).",
                          event)
        self.processing_done.wait()
        self.logger.info("Done processing memory with Volatility.")


def memory_snapshot(context, memory_dump_path, compress):
    # fix issue with libvirt's API
    open(memory_dump_path, 'a').close()  # touch file to set permissions

    dump_flag = libvirt.VIR_DUMP_MEMORY_ONLY
    if compress:
        dump_format = libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_KDUMP_ZLIB
    else:
        dump_format = libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_RAW

    context.domain.coreDumpWithFormat(memory_dump_path, dump_format, dump_flag)


def process_memory_snapshot(snapshot_path, profile, plugin):
    process = launch_process('volatility',
                             '--profile=%s' % profile,
                             '--filename=%s' % snapshot_path,
                             plugin)
    file_name = '%s_%s.log' % (snapshot_path.split('.')[0], plugin)

    collect_process_output(process, file_name)
