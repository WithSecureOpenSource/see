import sys
import mock
import unittest

from see import Hook
from see import context

from see.hooks import HookParameters


STATES = (context.NOSTATE, context.RUNNING, context.BLOCKED,
          context.PAUSED, context.SHUTDOWN, context.SHUTOFF,
          context.CRASHED, context.SUSPENDED)


class TestHook(Hook):
    def __init__(self, parameters):
        super(TestHook, self).__init__(parameters)
        self.pre_event = None
        self.post_event = None

    def pre_handler(self, event):
        self.pre_event = event

    def post_handler(self, event):
        self.post_event = event


class SeeContextFactoriesTest(unittest.TestCase):
    def test_qemu_context_factory(self):
        sys.modules['see.context.resources.qemu'] = mock.Mock()
        factory = context.QEMUContextFactory({})
        self.assertTrue(isinstance(factory('foo'), context.SeeContext))

    def test_lxc_context_factory(self):
        sys.modules['see.context.resources.lxc'] = mock.Mock()
        factory = context.LXCContextFactory({})
        self.assertTrue(isinstance(factory('foo'), context.SeeContext))

    def test_vbox_context_factory(self):
        sys.modules['see.context.resources.vbox'] = mock.Mock()
        factory = context.VBoxContextFactory({})
        self.assertTrue(isinstance(factory('foo'), context.SeeContext))


class SeeContextTest(unittest.TestCase):
    def setUp(self):
        self.resources = mock.Mock()
        self.context = context.SeeContext('foo', self.resources)
        self.hook = TestHook(HookParameters('foo', {}, self.context))

    def test_no_hypervisor(self):
        """RuntimeError is raised if hypervisor connection is not alive."""
        self.resources.hypervisor.isAlive.return_value = False
        with self.assertRaises(RuntimeError):
            self.context.hypervisor

    def test_no_storage(self):
        """RuntimeError is raised if storage_pool connection is not active."""
        self.resources.storage_pool.isActive.return_value = False
        with self.assertRaises(RuntimeError):
            self.context.storage_pool

    def test_no_network(self):
        """RuntimeError is raised if network is not active."""
        self.resources.network.isActive.return_value = False
        with self.assertRaises(RuntimeError):
            self.context.network

    def test_mac_addr(self):
        """MAC address is set if not present."""
        string_xml = """<domain>
                          <devices>
                            <interface type="network">
                              <mac address="00:00:00:00" />
                            </interface>
                          </devices>
                        </domain>"""
        self.context.domain.XMLDesc.return_value = string_xml

        self.assertEqual(self.context.mac_address, '00:00:00:00')
        self.assertEqual(self.context._mac_address, '00:00:00:00')

    def test_no_mac(self):
        """IPv4 address is None if no MAC address is provided."""
        string_xml = """<devices></devices>"""
        self.context.domain.XMLDesc.return_value = string_xml
        self.assertEqual(self.context.mac_address, None)
        self.assertEqual(self.context._mac_address, None)

    def test_ip4_addr(self):
        """IP address is set if not present."""
        string_xml = """<domain>
                          <devices>
                            <interface type="network">
                              <mac address="00:00:00:00" />
                            </interface>
                          </devices>
                        </domain>"""
        arptable = """0.0.0.0 something weird 00:00:00:00"""
        self.context.domain.XMLDesc.return_value = string_xml

        with mock.patch('see.context.context.open',
                        mock.mock_open(read_data=arptable),
                        create=True):
            self.assertEqual(self.context.ip4_address, '0.0.0.0')
            self.assertEqual(self.context._ip4_address, '0.0.0.0')

    def test_ip4_no_mac(self):
        """IPv4 address is None if no MAC address is provided."""
        string_xml = """<devices></devices>"""
        self.context.domain.XMLDesc.return_value = string_xml
        self.assertEqual(self.context.ip4_address, None)
        self.assertEqual(self.context._ip4_address, None)

    def test_ip4_no_address(self):
        """IPv4 address is None if ARP table lookup misses."""
        string_xml = """<domain>
                          <devices>
                            <interface type="network">
                              <mac address="00:00:00:00" />
                            </interface>
                          </devices>
                        </domain>"""
        arptable = """0.0.0.0 something weird 11:11:11:11"""
        self.context.domain.XMLDesc.return_value = string_xml

        with mock.patch('see.context.context.open',
                        mock.mock_open(read_data=arptable),
                        create=True):
            self.assertEqual(self.context.ip4_address, None)

    def test_state_transition(self):
        """State transition map is honoured."""
        for method in (self.context.poweron, self.context.resume,
                       self.context.pause, self.context.poweroff,
                       self.context.shutdown, self.context.restart):
            for state in STATES:
                self.context.domain.state.return_value = [state]
                if method.__name__ not in context.context.STATES_MAP[state]:
                    with self.assertRaises(RuntimeError):
                        method()

    def test_event_triggering(self):
        """Pre and Post event are triggered."""
        for method in (self.context.poweron, self.context.resume,
                       self.context.pause, self.context.poweroff,
                       self.context.restart):
            for state in STATES:
                if method.__name__ in context.context.STATES_MAP[state]:
                    self.context.domain.state.return_value = [state]
                    self.hook.context.subscribe('pre_%s' % method.__name__,
                                                self.hook.pre_handler)
                    self.hook.context.subscribe('post_%s' % method.__name__,
                                                self.hook.post_handler)
                    method()
                    self.assertEqual(self.hook.pre_event,
                                     'pre_%s' % method.__name__)
                    self.assertEqual(self.hook.post_event,
                                     'post_%s' % method.__name__)

    def test_shutdown_event_triggering(self):
        """Pre and Post shutdown is triggered."""
        self.context.domain.state.side_effect = [[1], [5]]
        self.hook.context.subscribe('pre_shutdown', self.hook.pre_handler)
        self.hook.context.subscribe('post_shutdown', self.hook.post_handler)
        self.context.shutdown()
        self.assertEqual(self.hook.pre_event, 'pre_shutdown')
        self.assertEqual(self.hook.post_event, 'post_shutdown')

    def test_shutdown_timeout(self):
        """RuntimeError is raised if shutdown times out."""
        self.context.domain.state.return_value = [1]
        with self.assertRaises(RuntimeError):
            self.context.shutdown(timeout=1)

    def test_cleanup(self):
        """Resources are released"""
        self.context.cleanup()
        self.assertTrue(self.resources.cleanup.called)
