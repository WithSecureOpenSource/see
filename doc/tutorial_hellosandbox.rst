Hello Sandbox
=============

Now that the basics are ready, we can start building our automated test environment.

Core elements of SEE consist of the Environment, which takes care of resources management, and the Context which wraps the sandbox allowing to control its lifecycle.

The following example shows the basic workflow. Once initialized the Context, we power on the sandbox, we let it run for one minute and then we power it off.

::

    import time

    from see import Environment
    from see.context import QEMUContextFactory


    def main():
        context_factory = QEMUContextFactory('/home/username/context.json')

        with Environment(context_factory, {}) as environment:
            context = environment.context

            context.poweron()

            time.sleep(60)

            context.poweroff()


    if __name__ == '__main__':
        main()

SEE takes care of the resources allocation/deallocation as well as for their isolation. This script can be executed multiple times resulting in multiple test environment running concurrently.

Once the execution ends, no trace will remain of the virtual machine.

Controlling the Sandbox
-----------------------

Every proper tutorial includes the "Hello World" example, we cannot be outdone.

To better control the execution flow, SEE provides an event-driven architecture allowing to trigger Events and subscribe handlers through the Context object.

In the next code snippet, we print the "Hello Sandbox" string after starting the sandbox. At the same time, we open a VNC connection to inspect its execution.

To complete the script, we turn it into a command line tool complete with parameters.

::

   #!/usr/bin/env python3

   import time
   import argparse
   import subprocess

   from see import Environment
   from see.context import QEMUContextFactory


   def hello_sandbox_handler(event):
       print("Hello Sandbox!")


   def vnc_handler(event):
       command = ('virt-viewer', '--connect', 'qemu:///system', event.identifier)
       subprocess.call(command)


   def main():
       arguments = parse_arguments()

       context_factory = QEMUContextFactory(arguments.context)

       with Environment(context_factory, {}) as environment:
           context = environment.context

           context.subscribe('vm_started', hello_sandbox_handler)

           # asynchronous handlers do not block the execution
           # when triggering the Event
           context.subscribe_async('vm_started', vnc_handler)

           context.poweron()

           # the Environment ID is appended to the event as extra information
           context.trigger('vm_started', identifier=environment.identifier)

           time.sleep(60)

           context.poweroff()


   def parse_arguments():
       parser = argparse.ArgumentParser(description='Run a Sandbox.')

       parser.add_argument('context', help='path to Context JSON configuration')

       return parser.parse_args()


   if __name__ == '__main__':
       main()

The above logic subscribes through the Context the handlers `hello_sandbox_handler` and `vnc_handler` to the `vm_started` Event. The Event is then triggered right after powering on the Context.

Once launched the script, a VNC session will be automatically opened showing us the guest OS. On the log we should see the "Hello Sandbox!" text.

::

   $ ./sandbox.py context.json

   Hello Sandbox!
