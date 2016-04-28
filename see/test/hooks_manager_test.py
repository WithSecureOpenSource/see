import copy
import mock
import unittest

from see import Hook
from see import hooks


CONFIG = {'configuration': {'key': 'value'},
          'hooks':
          [{'name': 'see.test.hooks_manager_test.TestHook',
            'configuration': {'foo': 'bar'}},
           {'name': 'see.test.hooks_manager_test.TestHookCleanup'}]}


class TestHook(Hook):
    def __init__(self, parameters):
        super(TestHook, self).__init__(parameters)
        self.cleaned = False


class TestHookCleanup(Hook):
    def __init__(self, parameters):
        super(TestHookCleanup, self).__init__(parameters)
        self.cleaned = False

    def cleanup(self):
        self.cleaned = True


class HookManagerLoadTest(unittest.TestCase):
    def setUp(self):
        self.hook_manager = hooks.HookManager('foo', copy.deepcopy(CONFIG))

    def test_load_hooks(self):
        """TestHook is loaded into HookManager."""
        context = mock.MagicMock()
        self.hook_manager.load_hooks(context)
        self.assertEqual(self.hook_manager.hooks[0].__class__.__name__,
                         'TestHook')

    def test_load_hooks_configuration(self):
        """Generic configuration are available in TestHook."""
        context = mock.MagicMock()
        self.hook_manager.load_hooks(context)
        self.assertTrue('key' in self.hook_manager.hooks[0].configuration)

    def test_load_hooks_specific_configuration(self):
        """Specific configuration are available in TestHook."""
        context = mock.MagicMock()
        self.hook_manager.load_hooks(context)
        self.assertTrue('foo' in self.hook_manager.hooks[0].configuration)

    def test_load_non_existing_hook(self):
        """Wrong Hooks are not loaded."""
        context = mock.MagicMock()
        config = copy.deepcopy(CONFIG)
        config['hooks'][0]['name'] = 'foo'
        config['hooks'][1]['name'] = 'bar'
        hm = hooks.HookManager('foo', config)
        hm.load_hooks(context)
        self.assertEqual(len(hm.hooks), 0)

    def test_load_missing_name(self):
        """Wrong Hooks are not loaded."""
        context = mock.MagicMock()
        config = copy.deepcopy(CONFIG)
        del config['hooks'][0]['name']
        hm = hooks.HookManager('foo', config)
        hm.load_hooks(context)
        self.assertEqual(len(hm.hooks), 1)


class HooksManagerCleanupTest(unittest.TestCase):
    def setUp(self):
        self.hook_manager = hooks.HookManager('foo', copy.deepcopy(CONFIG))

    def test_cleanup(self):
        """Cleanup is performed if specified."""
        context = mock.MagicMock()
        self.hook_manager.load_hooks(context)
        hook = self.hook_manager.hooks[1]
        self.hook_manager.cleanup()
        self.assertTrue(hook.cleaned)

    def test_no_cleanup(self):
        """Cleanup is not performed if not specified."""
        context = mock.MagicMock()
        self.hook_manager.load_hooks(context)
        hook = self.hook_manager.hooks[0]
        self.hook_manager.cleanup()
        self.assertFalse(hook.cleaned)
