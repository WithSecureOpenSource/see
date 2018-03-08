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

"""Module for acquiring and analysing disk snapshots of a running VM.

It depends on VMInspect library.

https://github.com/noxdafox/vminspect

"""

import os
import json
import libvirt
from threading import Event
import xml.etree.ElementTree as etree

from see import Hook
from vminspect import DiskComparator

from .utils import launch_process, collect_process_output, create_folder


QEMU_IMG = 'qemu-img'


class DiskCheckPointHook(Hook):
    """
    Disk checkpoint hook.

    On the given event, it takes a checkpoint of the disk's state.

    configuration::

        {
          "results_folder": "/folder/where/to/store/disk/checkpoints",
          "checkpoint_on_event": ["event_triggering_checkpoint"],
          "delete_checkpoints": False,
        }

    The checkpoint_on_event can be either a string representing the event
    or a list of multiple ones.

    If rebase is set to True, the disk checkpoints will be rebased
    on the original disk image and not the cloned one. This enables

    If delete_checkpoints is set to True, the disk checkpoints will be deleted
    at the end of the execution.

    """
    SNAPSHOT_XML = """
    <domainsnapshot>
      <name>{0}</name>
      <description>{1}</description>
    </domainsnapshot>
    """

    def __init__(self, parameters):
        super().__init__(parameters)
        self.checkpoints = []

        self.setup_handlers()

    def setup_handlers(self):
        if 'checkpoint_on_event' in self.configuration:
            configured_events = self.configuration['checkpoint_on_event']
            events = (isinstance(configured_events, str)
                      and [configured_events] or configured_events)

            for event in events:
                self.context.subscribe(event, self.disk_checkpoint_handler)
                self.logger.debug("Disk checkpoint registered at %s event",
                                  event)

    def disk_checkpoint_handler(self, event):
        self.logger.debug("Event %s: taking disk checkpoint.", event)

        checkpoint_path = self.disk_checkpoint(event)
        self.context.trigger("disk_checkpoint_taken", path=checkpoint_path)

        self.logger.info("Disk checkpoint %s taken.", checkpoint_path)

    def disk_checkpoint(self, event):
        volume = self.context.storage_pool.storageVolLookupByName(
            self.identifier)
        disk_snapshot = self.disk_snapshot(event)

        self.logger.info("DISK SNAPSHOT %s", disk_snapshot.getName())
        disk_path = snapshot_to_checkpoint(volume, disk_snapshot,
                                           self.configuration['results_folder'])
        self.checkpoints.append(disk_path)

        return disk_path

    def disk_snapshot(self, snapshot_name):
        snapshot_xml = self.SNAPSHOT_XML.format(snapshot_name,
                                                'Disk Checkpoint')
        return self.context.domain.snapshotCreateXML(snapshot_xml, 0)

    def cleanup(self):
        if self.configuration.get('delete_checkpoints', False):
            for disk in self.checkpoints:
                os.remove(disk)


class DiskStateAnalyser(Hook):
    """
    On the given event, it analyses the first two provided disk checkpoints.

    The disk checkpoint file paths must be communicated through
    a "disk_checkpoint_taken" event within its path attribute.

    Lists all the created, modified and deleted files.
    Extracts modified or newly created files.
    Lists all the created, modified and deleted Windows Registry
    Keys and Values.

    configuration::

        {
          "results_folder": "/folder/where/to/store/result/files",
          "identify_files": False,
          "get_file_size": False,
          "extract_files": False,
          "use_concurrency": False,
          "compare_registries": False,
          "start_processing_on_event": "event_starting_async_processing",
          "wait_processing_on_event": "event_waiting_async_processing"
        }

    A report will be written in the results_folder.

    Setting identify_files to True will add the file type to the report.
    If get_file_size is set, the file size will be added to the report.

    If extract_files is True, all modified and newly created files
    will be extracted from the second disk checkpoint.

    use_concurrency speeds up the processing by using multiple CPUs.

    If compare_registries is True, the windows registry will be compared.

    If delete_checkpoints is set to True, the disk checkpoints will be deleted
    at the end of the execution.

    On start_processing_on_event, the analysis process will be started
    with the given configuration.
    wait_processing_on_event allows to wait for the analysis process
    to terminate.

    """
    def __init__(self, parameters):
        super().__init__(parameters)
        self.checkpoints = []
        self.setup_handlers()
        self.processing_done = Event()

    def setup_handlers(self):
        self.context.subscribe('disk_checkpoint_taken',
                               self.disk_checkpoint_handler)

        if {'start_processing_on_event',
            'wait_processing_on_event'} <= set(self.configuration):
            event = self.configuration['start_processing_on_event']
            self.context.subscribe_async(event, self.start_processing_handler)
            self.logger.debug("FileSystem analysis scheduled at %s event",
                              event)

            event = self.configuration['wait_processing_on_event']
            self.context.subscribe(event, self.stop_processing_handler)
            self.logger.debug("FileSystem analysis wait at %s event", event)

    def disk_checkpoint_handler(self, event):
        if hasattr(event, 'path'):
            self.logger.debug("Event %s: new disk checkpoint %s.",
                              event, event.path)
            self.checkpoints.append(event.path)
        else:
            self.logging.warning("%s event received, no path specified.")

    def start_processing_handler(self, event):
        """Asynchronous handler starting the disk analysis process."""
        results_path = os.path.join(self.configuration['results_folder'],
                                    "filesystem.json")
        self.logger.debug("Event %s: start comparing %s with %s.",
                          event, self.checkpoints[0], self.checkpoints[1])

        results = compare_disks(self.checkpoints[0], self.checkpoints[1],
                                self.configuration)

        with open(results_path, 'w') as results_file:
            json.dump(results, results_file)

        self.processing_done.set()

    def stop_processing_handler(self, event):
        self.logger.debug(
            "Event %s: waiting for File System state comparison.", event)
        self.processing_done.wait()
        self.logger.info("File System state comparison concluded.")


def snapshot_to_checkpoint(volume, snapshot, folder_path):
    """Turns a QEMU internal snapshot into a QCOW file."""
    create_folder(folder_path)

    name = snapshot.getName()
    path = os.path.join(folder_path, '%s.qcow2' % name)

    process = launch_process(QEMU_IMG, "convert", "-f", "qcow2", "-o",
                             "backing_file=%s" % volume_backing_path(volume),
                             "-O", "qcow2", "-s", name,
                             volume_path(volume), path)
    collect_process_output(process)

    return path


def compare_disks(disk0, disk1, configuration):
    """Compares two disks according to the given configuration."""
    with DiskComparator(disk0, disk1) as comparator:
        results = comparator.compare(
            size=configuration.get('get_file_size', False),
            identify=configuration.get('identify_files', False),
            concurrent=configuration.get('use_concurrency', False))

        if configuration.get('extract_files', False):
            extract = results['created_files'] + results['modified_files']
            files = comparator.extract(1, extract,
                                       path=configuration['results_folder'])

            results.update(files)

        if configuration.get('compare_registries', False):
            results['registry'] = comparator.compare_registry(
                concurrent=configuration.get('use_concurrency', False))

    return results


def volume_path(volume):
    volume_xml = volume.XMLDesc()
    volume_element = etree.fromstring(volume_xml)

    return volume_element.find('.//target/path').text


def volume_backing_path(volume):
    volume_xml = volume.XMLDesc()
    volume_element = etree.fromstring(volume_xml)

    return volume_element.find('.//backingStore/path').text
