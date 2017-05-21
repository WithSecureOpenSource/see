Plugins and Protocol
====================

In the previous chapter we created a Sandbox with a minimal set of functionalities.

As the number of features grows, so does the complexity of the system. SEE has been designed to contain the development cost providing high flexibility and promoting code re-usability.

As shown previously, the Context allows to subscribe event handlers and trigger Events. This is commonly referred as the `Observer <https://en.wikipedia.org/wiki/Observer_pattern>`_ pattern.

Rather than adding additional features, let's try to encapsulate the ones we already provided in a re-usable module.

The Plugins
-----------

If the Context is an observable, the Hooks or plugins play the observer's role. They can register their handlers to the desired Events using them as a mean of synchronisation.

The Environment class accepts an arbitrary amount of Hooks. Once initialized, each Hook receives a reference to the Context and its own specific configuration.

Here follows as an example the VNC Hook. To make it more generic, we allow the User to configure at which Event to open the VNC connection.

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
               self.context.subscribe_async(self.configuration['start_vnc'], self.vnc_handler)

       def vnc_handler(self, event):
           self.logger.info("Event %s: starting VNC connection.", event)

           command = ('virt-viewer', '--connect', 'qemu:///system', self.identifier)
           subprocess.call(command)

The Protocol
------------

In the natural sciences a `protocol <https://en.wikipedia.org/wiki/Protocol_%28science%29>`_ is a predefined written procedural method in the design and implementation of experiments. When writing test cases to analyse unknown samples, we define a protocol as a sequence of instructions affecting the Context and leading to several Events to be triggered.

With a well defined set of protocols and a collection of independent plugins, we can assemble a vaste amount of test cases without the need of writing any specific code.

The protocol will act on the Context which will be observed by the Hooks and the Events will be the transport mechanism for such protocol.

::

   TIMEOUT = 60
   RUNTIME = 60


   def protocol(context, sample_path, execution_command):
       context.poweron()

       wait_for_ip_address(context, TIMEOUT)

       context.trigger('run_sample', sample=sample_path, command=execution_command)

       time.sleep(RUNTIME)

       context.pause()
       context.trigger('snapshots_capture')
       context.resume()

       context.shutdown()

       context.trigger('start_analysis')
       context.trigger('wait_analysis')


   def wait_for_ip_address(context, timeout):
       timestamp = time.time()

       while time.time() - timestamp < timeout:
           if context.ip_address is not None:
               context.trigger('ip_address', address=context.ip_address)
               return

           time.sleep(1)

       raise TimeoutError("Waiting for IP address")

The above example is pretty simple to understand. After powering on the Sandbox, we wait for its IP address to be ready. We then inject the sample and let it run for a given amount of time. We notify the plugins that the VM is about to be shut down letting them capture any necessary information. Once powered off the VM, we proceed analysing the gathered information.

The Event sequence is the following.

  Triggered by the `Context.poweron` method:

  - pre_poweron
  - post_poweron

  Triggered by the `wait_for_ip_address` function once the IP address is available:

  - ip_address

  Triggered in order to start start the sample:

  - run_sample

  Triggered by the `Context.pause` method:

  - pre_pause
  - post_pause

  Triggered in order to take snapshots of the virtual machine state:

  - snapshots_capture

  Triggered by the `Context.resume` methods:

  - pre_resume
  - post_resume

  Triggered by the `Context.shutdown` method:

  - pre_shutdown
  - post_shutdown

  Triggered in order to start analysis plugins:

  - start_analysis
  - wait_analysis

-------------

To conclude the chapter, we show the new script. The sample path, its execution command as well as the Hooks configuration path have been parametrised.

Refer to the `Documetation <http://pythonhosted.org/python-see/user.html#hooks>`_ to configure the Hooks.

::

   #!/usr/bin/env python3

   import time
   import argparse

   from see import Environment
   from see.context import QEMUContextFactory


   TIMEOUT = 60
   RUNTIME = 60


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

       context.trigger('snapshots_capture')

       context.poweroff()

       context.trigger('start_analysis')
       context.trigger('wait_analysis')


   def wait_for_ip_address(context, timeout):
       timestamp = time.time()

       while time.time() - timestamp < timeout:
           if context.ip4_address is not None:
               context.trigger('ip_address', address=context.ip4_address)
               return

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
