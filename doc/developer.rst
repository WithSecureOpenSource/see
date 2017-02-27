Developer Manual
================

This section describes how to further develop the SEE Platform. The core interfaces are introduced at first. It will follow an in depth description of the provided implementations.

The Context Interface
---------------------

A Context is an `Observable <https://en.wikipedia.org/wiki/Observer_pattern>`_ object. It allows multiple plugin objects - named Hooks - to operate over it and notifies them back through Events.

A Context must be followed by a Factory function which, when called, receives the Environment identifier and returns the fully functional Context object.

The Developer can extend the Context class to provide his/her own Sandbox implementation. The newly implemented class will need to provide a `cleanup` method which will be called during the Environment de-allocation phase which occurs at the end of the Test Case execution. All the Event related mechanisms will be provided by the parent class.

The Hook Interface
------------------

A Hook is an `Observer <https://en.wikipedia.org/wiki/Observer_pattern>`_ object. It allows the plugin to control the given Context driving the Test Case lifecycle. Through the Context, the Hook can subscribe and unsubscribe its Handlers to the Events. The Handlers will be called at the triggering of the given Event and will receive the Event itself as parameter.

The Developer can extend the Hook class to provide his/her plugins for driving the Test Case execution. The Developer can override the Hook's `cleanup` method to remove temporary resources during the Environment de-allocation phase which occurs at the end of the Test Case execution.

The parent class provides as well a logger object and the configuration values specified by the User in the Hooks configuration.

The Resources Interface
-----------------------

The Resources interface has been initially introduced as an adapter between the Context and `libvirt` API interface. It is a generic interface for the Sandbox resource provisioning and management.

The Developer can implement the Resource class to encapsulate his/her own Sandbox provider.

The Resources interfaces expose an allocation and de-allocation method and accepts an identifier and a configuration for its constructor parameters.

The SEE Context and its Factories employ the Resources interface to abstract the `libvirt` API.

The ImageProvider Interface
---------------------------

The ImageProvider interface facilitates a system of plugins to retrieve disk images from arbitrary sources.

The Developer can implement the ImageProvider class to encapsulate his/her own disk image provider.

The ImageProvider interface exposes a single `image` property. This property is expected to be a string representing an absolute path to the image file, locally available to the Context. The class implementing this interface is expected to hold the logic to retrieve the disk image and store it locally in the path returned by the image property.

The Environment Class
---------------------

The User can spawn multiple isolated instances consisting in separate Test Cases through the Environment class. Each instance requires a Context Factory callable and its Hooks specific configuration.

The example code is a simple yet quite complete example of usage of the Environment class.

::

  from time import time
  from see import Environment
  from see.resources import QemuFactory


  context_factory = QemuFactory('/path/to/resources/configuration.json')


  with Environment(context_factory, '/path/to/hooks/configuration.json') as environment:
      context = environment.context

      context.poweron()

      ip_address = wait_for_ip_address(context)
      context.trigger('got_ip_address', address=ip_address)

      time.sleep(180)

      context.poweroff()


  def wait_for_ip_address(context):
      while 1:
          if context.ip4_address is not None:
              return context.ip4_address
          else:
              time.sleep(1)

A QemuFactory class is employed to provide a Context Factory callable to the Environment. The Environment receives the Context Factory and the path to the Hooks configuration file. The Environment class implements the Python Context Manager protocol (PEP-343) allowing to encapsulate the `allocate` and `deallocate` methods in the `with` statement.

Once allocated the Environment, its Context is retrieved in order to power on the Sandbox. The `poweron` method triggers a `pre_poweron` and a `post_poweron` Events to the installed Hooks.

In order to detect when the guest Operating System has terminated its boot procedure, the Context `ip4_address` attribute is polled. If the network interface is using DHCP server for its address assignment, the Context `ip4_address` attribute will become available only once the IP address will be correctly assigned to the guest. Most of the Operating Systems request an IP address at the end of their boot routine.

The guest IP address is then forwarded to the Hooks as an appended attribute to the `got_ip_address` attribute.

Three minutes are then waited in order to allow the Hooks to perform their duties and then, the Sandbox is powered off triggering a `pre_poweroff` and a `post_poweroff` Events.

The Resources Class
-------------------

The SEE Resources Classes implements the Sandbox provisioning machinery and expose its internals to the Hooks Developers.

The class constructor receives the Environment identifier and the Resources specific configuration. Once the object has been initialised, the Developer can call its `allocate` method to build the specific Sandbox.

The Resources interface contract can be found in the following file:

::

   see/context/resources/resources.py

The Resources object is characterised by four attributes which are derived from libvirt's specific terminology.

hypervisor
++++++++++

The Hypervisor connection represent the handler to the Sandbox provisioning controller. Resources are allocated and de-allocated through this object. Hooks Developers might use this handler to instruct the provisioning controller about some group specific property or to handle failures whenever the other resources become corrupted. In libvirt name space this object directly correlates with the `virConnectPtr` object.

domain
++++++

The Domain encapsulates the specific sandbox instance, allowing the Hooks to directly access to its state. The Context object employs this attribute to realise the state-change machinery and the Hooks Developers might access to the sandbox memory or CPU through it. In libvirt name space this object directly correlates with the `virDomainPtr` object.

storage_pool
++++++++++++

The Storage Pool contains all the Disks associated to the sandbox instance. In libvirt name space this object directly correlates with the `virStoragePool` object.

network
+++++++

The Network object represents the network to which the sandbox is connected. In libvirt name space this object directly correlates with the `virNetwork` object.

A `deallocate` method will be called at the end of the Environment's lifecycle, it's responsibility is to free the Sandbox specific resources.

The Context Class
-----------------

The SEE Context class wraps the resources allocated within the Resources Class and takes care of providing thread safe access from the Hooks.

The following methods are exposed via the Context:

  - poweron: Starts the virtual machine and triggers the pre\_poweron and post\_poweron events.
  - pause: Suspends the virtual machine and triggers the pre\_pause and post\_pause events.
  - resume: Resumes the suspended virtual machine and triggers the pre\_resume and post\_resume events.
  - restart: Restarts the virtual machine and triggers the pre\_reboot and post\_reboot events.
  - poweroff: Stops the virtual machine and triggers the pre\_poweroff and post\_poweroff events. This method is the equivalent of a power cut to a running machine.
  - shutdown: Sends a shutdown request to the virtual machine and triggers the pre\_shutdown and post\_shutdown events. This method blocks until the Sandbox has not shut down or until the given timeout has expired. The method will block indefinitely if the guest Operating System does not handle correctly the shutdown request.

The Resources de-allocation is performed in the SEE Context `cleanup` method.

The Context Factory
-------------------

The Context Factories are callable which receive the Environment identifier when called and are supposed to return a functional Context object.

The example in picture shows how the QEMU Context Factory is realised.

::

  from see.context import SEEContext
  from see.context.resources import QemuResources


  class QemuFactory(object):
      def __init__(self, configuration):
          self.configuration = configuration

      def __call__(self, identifier):
          """Called by the Environment allocate() method."""
          resources = QemuResources(identifier, self.configuration)

          try:
              resources.allocate()
          except Exception:
              resources.deallocate()
              raise

          return SEEContext(identifier, resources)

The Hooks
---------

A Hooks is an Observer class which receives a reference to the Context and uses it to drive the Test Case.

The code block shows a quite exhaustive example of a Hook.

::

  from see import Hook
  from time import time
  from utils import delete_folder


  class ExampleHook(Hook):
      """Example Hook"""
      def __init__(self, *args):
          super(ExampleHook, self).__init__(*args)
          self.setup_handlers()

      def setup_handlers(self):
          self.context.subscribe_async('post_poweron', self.poweron_event_handler)
          self.context.subscribe('custom_event', self.custom_event_handler)
          self.context.subscribe('post_pause', self.pause_event_handler)

      def poweron_event_handler(self, event):
          """This handler is run asynchronously. It does not block the Event flow"""
          self.logger.info("%s event received, the Context is powered on", event)
          time.sleep(60)
          self.context.trigger('custom_event')  # fire an Event to all Hooks

      def custom_event_handler(self, event):
          """This Handler is run synchronously and powers off the Context."""
          self.context.pause()

      def pause_event_handler(self, event):
          """Event Handler for the last event (post_paused)."""
          self.logger.info("%s event received, the Context is paused", event)

      def cleanup(self):
          """
          If defined, this method will be executed during the Environment de-allocation.
          It allows the Developer to cleanup temporary resources.
          """
          if 'temporary_folder' in self.configuration:
              delete_folder(self.configuration['temporary_folder'])

Each Handler is run synchronously. This means that only a Handler at a time can be executed and triggering an Event will block the execution until all the subscribed Handlers have been consumed. In case this is not the desired behaviour, the Developer can subscribe asynchronous Handlers which will run concurrently without blocking the execution flow.

In the example an asynchronous Handler is subscribed to the `post_poweron` Event. Its Handler waits for a minute and then triggers a custom Event. The custom Event is handled by the `custom_event_handler` Handler which pauses the Context triggering a `pre_pause` and a `post_pause` Events. The Hook reacts to the `post_pause` through the `pause_event_handler` Handler and then waits for the Environment de-allocation in which cleans up the configured `temporary_folder`

The next example shows a possible implementation of a Hook which captures screenshots of the guest Operating System. The User can specify at which Events the screenshots should be taken through the `screenshot_on_event` configuration key.

::

  from see import Hook
  from see.context import RUNNING, PAUSED
  from utils import create_folder, take_screenshot


  class ScreenHook(Hook):
      """
      Screenshot capturing hook.

      On the given event, it captures the Context's screen on a PPM file in the given folder. The "screenshot_on_event" can be either a string representing the event or a list of multiple ones.

      configuration::

          {
            "results_folder": "/folder/where/to/store/screenshots/",
            "screenshot_on_event": ["post_poweron", "custom_event1", "custom_event2"]
          }

      """
      def __init__(self, parameters):
          super(ScreenHook, self).__init__(parameters)
          self.setup_handlers()

      def setup_handlers(self):
          if 'screenshot_on_event' in self.configuration:
              configured_events = self.configuration['screenshot_on_event']
              events = (isinstance(configured_events, basestring)
                        and [configured_events] or configured_events)

              for event in events:
                  self.context.subscribe(event, self.capture_screenshot)
                  self.logger.debug("Screenshot registered at %s event", event)

      def capture_screenshot(self, event):
          folder_path = self.configuration['results_folder']
          screenshot_path = os.path.join(folder_path, "%s_%s.ppm"
                                       % (self.identifier, event))
          self.logger.info("Event %s: capturing screenshot.", event)

          create_folder(folder_path)
          self.screenshot(screenshot_path)

          self.logger.info("Screenshot %s captured.", screenshot_path)

      def screenshot(self, screenshot_path):
          self.assert_context_state()

          with open(screenshot_path, 'wb') as screenshot_file:
              screenshot_stream = take_screenshot(self.context)
              screenshot_file.write(screenshot_stream)

      def assert_context_state(self):
          if self.context.domain.state()[0] not in (RUNNING, PAUSED):
              raise RuntimeError("Cannot capture screenshots of a shutdown Contex")

The Events
----------

The Events represent the communication interface between the Hooks and the Environment in which they are executed. Once an event is fired, all the Hooks which subscribed one or more of their Handlers will execute them.

Events are represented by a class, which extends a Python string, to which extra information is appended as attributes. To fire an Event, a Hook must use the Context `trigger` method which accepts as parameters either an Event instance or more simply a string and a set of keyword arguments. In the latter case, an Event object will be built from the given string and the keyword arguments will be appended to it as attributes.

The Hook handlers will receive the dispatched Event as argument with the attributes `origin` carrying the Python's fully qualified name of the actor which generated it and `timestamp` representing the moment in which the Event has fired.

SEE is well suited for a `model-view-controller <https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller>`_ type of design. The model is represented by the Context Class, the view are the Events flowing through the Hooks and the controller could be either the Hooks in charge of acting as decision-maker or the Environment user.

Context specific Events
-----------------------

The Context implementation provided by SEE triggers a set of default events every time its state transition methods are called. Each state transition operated through the Context triggers two Events: a `pre_transition` which precedes the transition itself and a `post_transition` one, triggered after the Context is in its new state.

These events allow the Hooks to synchronise with the Sandbox state in order to perform actions requiring certain states. Taking a snapshot of the Sandbox memory state, for example, requires the virtual machine to be paused in order to get coherent data.

The Developer must keep in mind that triggering a Context state change while reacting to another one is a dangerous approach. It is highly recommended as well, not to perform any long lasting operation during the Handling of these specific Events. If the latter case cannot be avoided, the Developer can rely on the asynchronous Handlers to prevent heavy routines to significantly slow down the Event processing.

Below are listed the Events generated by default by the Context.

pre_poweron
+++++++++++

Triggered by the Context `poweron` method.

This Event is fired before powering on the Context, therefore the Context state is supposed to be shutoff.

post_poweron
++++++++++++

Triggered by the Context `poweron` method.

This Event is fired after powering on the Context, therefore the Context state is supposed to be running.

pre_pause
+++++++++

Triggered by the Context `pause` method.

This Event is fired before suspending the Context, therefore the Context state is supposed to be running.

post_pause
++++++++++

Triggered by the Context `pause` method.

This Event is fired after suspending the Context, therefore the Context state is supposed to be paused.

pre_resume
++++++++++

Triggered by the Context `resume` method.

This Event is fired before resuming the Context from suspension, therefore the Context state is supposed to be paused.

post_resume
+++++++++++

Triggered by the Context `resume` method.

This Event is fired after resuming the Context from suspension, therefore the Context state is supposed to be running.

pre_poweroff
++++++++++++

Triggered by the Context `poweroff` method.

This Event is fired before forcing the Context to power off, therefore the Context state is supposed to be either running or paused.

post_poweroff
+++++++++++++

Triggered by the Context `poweroff` method.

This Event is fired after forcing the Context to power off, therefore the Context state is supposed to be shutoff.

pre_shutdown
++++++++++++

Triggered by the Context `shutdown` method.

This Event is fired before requesting the guest Operating System to shut down , therefore the Context state is supposed to be running.

post_shutdown
+++++++++++++

Triggered by the Context `shutdown` method.

This Event is fired after requesting the guest Operating System to shut down , therefore the Context state is supposed to be shutdown.

pre_restart
+++++++++++

Triggered by the Context `restart` method.

This Event is fired before requesting the guest Operating System to restart, therefore the Context state is supposed to be either running or crashed.

post_restart
++++++++++++

Triggered by the Context `restart` method.

This Event is fired after requesting the guest Operating System to restart, therefore the Context state is supposed to be running.

Environment lifecycle
---------------------

To ensure a Sandbox with a high level of security, for each Test Case all the needed Resources are created at the moment of the request and completely destroyed once the Environment is not necessary anymore.

An Environment has its own lifecycle starting from the moment in which its `allocate` method is called and ending with the `deallocate` method invocation. It is the User's and the Developer's responsibility to store and process the execution data as after the Environment de-allocation, all the Sandbox Resources and the Hooks won't be accessible anymore.

An example of a typical Environment lifecycle could be:

  - Generation of the Sandbox and the Hooks configurations.
  - Initialisation of the Context Factory callable object.
  - Initialisation of the Environment.
  - Allocation of the Environment.
  - Guest Operating System power on through the Context `poweron` method.
  - Injection of the Sample via networking or other mean.
  - Execution of the Test Case.
  - Tracing of the Sample behaviour through the configured Hooks.
  - Guest Operating System power off through the Context `shutdown` or `poweroff` methods.
  - Data collection and analysis via the configured Hooks.
  - Data storage according to configuration.
  - Environment deletion and resources release.

Lifecycle traceability
----------------------

To each Environment object is assigned a Universally Unique IDentifier (UUID), it is recommended to use the same identifier for all the involved parts as it helps to address the complete history of a Test Case instance.

The Resources provided by SEE are all sharing the same identifier simplifying the clean-up process.
