Sample Execution
================

In order to study the behaviour of an unknown sample, we need to automate its injection and execution. To do so, we will use a Python HTTP server running as an agent within the Guest Operating System.

The Agent
---------

As specified in the setup chapter, Python 3 is required in order to run the agent.

The agent code can be fount at `this link <https://github.com/F-Secure/see/blob/master/plugins/agent.py>`_.

The easiest way to ensure its execution at the Windows startup is to place a batch script like the following in the startup folder.

::

   C:\path\to\the\Python\Installation\python.exe C:\path\to\the\agent\agent.py 0.0.0.0 8080

The startup folder is usually located at the following path:

::

   C:\Microsoft\Windows\Start Menu\Programs\Startup

The script will listen to the port 8080, make sure the firewall will allow traffic through such port.

At reboot, a command prompt should show the agent log. In case of issues, add the `---debug` parameter to the agent to better follow the exchanged messages.

The Commands Hook
-----------------

The `Commands Hook <https://github.com/F-Secure/see/blob/master/plugins/commands.py>`_ has been designed to be used altogether with the agent.

The only configuration parameter is the agent port. The Hook will automatically detect the IP address of the Sandbox. To add it to the analysis environment, add the following snippet to the Hooks configuration.

::

   {
       "name": "plugins.commands.CommandsHook",
       "configuration": {
           "agent-port": 8080
       }
   }

We can now run the script of the previous chapter as follows.

::

   $ ./sandbox.py context.json example.exe --hooks hooks.json --command "start {sample}"
