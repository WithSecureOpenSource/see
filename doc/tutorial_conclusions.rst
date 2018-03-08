Conclusion
==========

The automated analysis environment presented in the Tutorial is far from complete. Aim of the Tutorial was to show the potential of the SEE framework.

SEE aims to simplify the development of sandbox based behavioural analysis platforms focusing in providing multiple sandboxing technologies and a simple event driven architecture.

The effectiveness of the platform in identifying threats and analysing unknown software is in the plugins and the protocols provided by the developers. With a comprehensive collection of plugins, the User will be able to quickly assemble his or her own test cases without the need of writing any further logic.

A small set of reference plugins is available at this `link <https://github.com/F-Secure/see/tree/master/plugins>`_.

Resources
---------

Here follows the source code and configuration used in the examples.

`sandbox.py`

::

   #!/usr/bin/env python3

   import time
   import argparse

   from see import Environment
   from see.context import QEMUContextFactory

   TIMEOUT = 60
   RUNTIME = 600

   def main():
       arguments = parse_arguments()

       context_factory = QEMUContextFactory(arguments.context)

       with Environment(context_factory, arguments.hooks) as environment:
           protocol(environment.context, arguments.sample, arguments.command)

   def protocol(context, sample_path, execution_command):
       context.poweron()

       wait_for_ip_address(context, TIMEOUT)

       context.trigger('run_sample', sample=sample_path, command=execution_command)

       time.sleep(RUNTIME)

       context.pause()
       context.trigger('snapshots_capture')
       context.resume()

       context.shutdown(timeout=TIMEOUT)

       context.trigger('start_analysis')
       context.trigger('wait_analysis')

   def wait_for_ip_address(context, timeout):
       timestamp = time.time()

       while time.time() - timestamp < timeout:
           if context.ip4_address is not None:
               context.trigger('ip_address', address=context.ip4_address)
               return

           time.sleep(1)

       raise TimeoutError("Waiting for IP address")

   def parse_arguments():
       parser = argparse.ArgumentParser(description='Execute a sample within a Sandbox.')

       parser.add_argument('context', help='path to Context JSON configuration')
       parser.add_argument('sample', help='path to Sample to execute')
       parser.add_argument('-k', '--hooks', default={}, help='path to Hooks JSON configuration')
       parser.add_argument('-c', '--command', default='start {sample}',
                           help="""command used to start the sample.
                           The string {sample} will be expanded to the actual file name within the guest.
                           Example: 'notepad.exe {sample}'""")

      return parser.parse_args()

   if __name__ == '__main__':
       main()

`vnc.py`

::

   """VNC Hook.

   Opens a VNC connection with the Guest at the given event.

   Configuration:

      {
        "start_vnc": "event_at_which_starting_vnc"
      }

   """

   import subprocess

   from see import Hook


   class VNCHook(Hook):
       def __init__(self, parameters):
           super().__init__(parameters)

           if 'start_vnc' in self.configuration:
               self.context.subscribe_async(
                   self.configuration['start_vnc'], self.vnc_handler)

       def vnc_handler(self, event):
           self.logger.info("Event %s: starting VNC connection.", event)

           command = ('virt-viewer', '--connect',
                      'qemu:///system', self.identifier)
           subprocess.call(command)

`hooks.json`

::

   {
       "configuration":
       {
           "results_folder": "/home/username/results/"
       },
       "hooks":
       [
           {
               "name": "vnc.VNCHook",
               "configuration": {
                   "start_vnc": "post_poweron"
               }
           },
           {
               "name": "plugins.screen.ScreenHook",
               "configuration": {
                   "screenshot_on_event": ["snapshots_capture"]
               }
           },
           {
               "name": "plugins.commands.CommandsHook",
               "configuration": {
                   "agent-port": 8080
               }
           },
           {
               "name": "plugins.disk.DiskCheckPointHook",
               "configuration": {
                   "checkpoint_on_event": ["ip_address", "post_shutdown"],
                   "delete_checkpoints": true
               }
           },
           {
               "name": "plugins.disk.DiskStateAnalyser",
               "configuration": {
                   "identify_files": true,
                   "get_file_size": true,
                   "extract_files": false,
                   "use_concurrency": true,
                   "compare_registries": true,
                   "start_processing_on_event": "start_analysis",
                   "wait_processing_on_event": "wait_analysis"
               }
           },
           {
               "name": "plugins.memory.MemoryHook",
               "configuration": {
                   "memory_snapshots_on_event": ["snapshots_capture"],
                   "delete_snapshots": true
               }
           },
           {
               "name": "plugins.memory.VolatilityHook",
               "configuration": {
                   "start_processing_on_event": "start_analysis",
                   "wait_processing_on_event": "wait_analysis",
                   "profile": "Win7SP1x86",
                   "plugins": ["mutantscan", "psscan"]
               }
           },
           {
               "name": "plugins.network.NetworkTracerHook",
               "configuration": {
                   "start_trace_on_event": "ip_address",
                   "stop_trace_on_event": "post_shutdown",
                   "delete_trace_file": true
               }
           },
           {
               "name": "plugins.network.NetworkAnalysisHook",
               "configuration": {
                   "start_processing_on_event": "start_analysis",
                   "wait_processing_on_event": "wait_analysis",
                   "log_format": "text"
             }
         }
       ]
   }

`context.json`

::


   {
       "hypervisor": "qemu:///system",
       "domain":
       {
           "configuration": "/home/username/windows7.xml"
       },
       "disk":
       {
           "image":
           {
               "uri": "/home/username/images/IE8_-_Win7-disk1.qcow2",
               "provider": "see.image_providers.DummyProvider"
           },
           "clone":
           {
               "storage_pool_path": "/home/username/instances",
               "copy_on_write": true
           }
       },
       "network":
       {
           "dynamic_address":
           {
               "ipv4": "192.168.0.0",
               "prefix": 16,
               "subnet_prefix": 24
           }
       }
   }
