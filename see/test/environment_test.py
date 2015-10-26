import time
import unittest
import threading

from see import Environment, Hook, Context


class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        config = {'hooks': [{'name': 'see.test.environment_test.TestHook'},
                            {'name': 'see.test.environment_test.WrongHook'}]}
        self.environment = Environment(context_factory, config)
        self.environment.allocate()

    def tearDown(self):
        self.environment.deallocate()

    def test_trigger_simple_event(self):
        """Environment's events are propagated to Hooks."""
        self.environment.context.trigger('event1')
        self.assertTrue(self.environment._hookmanager.hooks[0].called1)

    def test_trigger_event_async_handler(self):
        """Environment's events are propagated to Hooks."""
        self.environment.context.trigger('event1')
        hook = self.environment._hookmanager.hooks[0]
        hook.async_called.wait()
        self.assertTrue(hook.async_called.is_set())

    def test_trigger_complex_event(self):
        """Environment's events attributes are propagated to Hooks."""
        self.environment.context.trigger('event2', arg='foo')
        self.assertEqual(self.environment._hookmanager.hooks[0].event_arg,
                         'foo')

    def test_sync_cascade_event(self):
        """Events which synchronous handlers trigger other ones."""
        self.environment.context.trigger('cascade_sync')
        hook = self.environment._hookmanager.hooks[0]
        hook.async_called.wait()
        self.assertTrue(hook.async_called.is_set())
        self.assertTrue(self.environment._hookmanager.hooks[0].called1)

    def test_async_cascade_event(self):
        """Events which asynchronous handlers trigger other ones."""
        self.environment.context.trigger('cascade_async')
        hook = self.environment._hookmanager.hooks[0]
        hook.async_called.wait()
        self.assertTrue(hook.async_called.is_set())
        self.assertTrue(self.environment._hookmanager.hooks[0].called1)

    def test_trigger_handler_error(self):
        """Exceptions within synchronous handlers won't stop the execution."""
        self.environment.context.trigger('error_event')
        self.assertTrue(self.environment._hookmanager.hooks[1].error_handler_called)

    def test_trigger_async_handler_error(self):
        """Exceptions within asynchronous handlers won't stop the execution."""
        self.environment.context.trigger('async_error_event')
        hook = self.environment._hookmanager.hooks[1]
        hook.error_async_handler_called.wait()
        self.assertTrue(self.environment._hookmanager.hooks[1].error_async_handler_called.is_set())

    def test_cleanup(self):
        """Environment's hooks are cleaned up on deallocate."""
        hook = self.environment._hookmanager.hooks[0]
        self.environment.deallocate()
        self.assertTrue(hook.clean)

    def test_cleanup_hook_error(self):
        """Errors in hooks cleanup are handled."""
        hook = self.environment._hookmanager.hooks[1]
        self.environment.deallocate()
        self.assertTrue(hook.clean)

    def test_cleanup_context_error(self):
        """Errors in context cleanup are handled."""
        config = {'hooks': [{'name': 'see.test.environment_test.WrongHook'}]}
        with Environment(wrong_context_factory, config) as environment:
            context = environment.context
        self.assertTrue(context.clean)

    def test_no_context(self):
        """RuntimeError raised if the Environment has not been initialized."""
        environment = Environment(context_factory, {})
        with self.assertRaises(RuntimeError):
            context = environment.context
            context.poweron()

    def test_unsubscribe(self):
        """Handler is unsubscribed."""
        hook = self.environment._hookmanager.hooks[0]
        hook.context.unsubscribe('event1', hook.handler1)
        self.environment.context.trigger('event1')
        self.assertFalse(hook.called1)

    def test_unsubscribe_async(self):
        """Async handler is unsubscribed."""
        hook = self.environment._hookmanager.hooks[0]
        hook.context.unsubscribe('event1', hook.async_handler)
        self.environment.context.trigger('event1')
        time.sleep(0.1)
        self.assertFalse(hook.async_called.is_set())

    def test_unsubscribe_no_such_event(self):
        """Error is raised if the given event is not registered."""
        hook = self.environment._hookmanager.hooks[0]
        with self.assertRaises(ValueError):
            hook.context.unsubscribe('event42', hook.handler1)

    def test_unsubscribe_no_such_handler(self):
        """Error is raised if the given handler is not registered."""
        hook = self.environment._hookmanager.hooks[0]
        with self.assertRaises(ValueError):
            hook.context.unsubscribe('event1', hook.cleanup)


def context_factory(identifier):
    return Context(identifier)


def wrong_context_factory(identifier):
    return WrongContext(identifier)


class TestHook(Hook):
    def __init__(self, parameters):
        super(TestHook, self).__init__(parameters)
        self.context.subscribe('event1', self.handler1)
        self.context.subscribe_async('event1', self.async_handler)
        self.context.subscribe('event2', self.handler2)
        self.context.subscribe('cascade_sync', self.cascade_handler)
        self.context.subscribe('cascade_async', self.cascade_async_handler)
        self.called1 = False
        self.event_arg = None
        self.clean = False
        self.async_called = threading.Event()

    def handler1(self, event):
        self.called1 = True

    def handler2(self, event):
        if hasattr(event, 'arg'):
            self.event_arg = event.arg

    def async_handler(self, event):
        self.async_called.set()

    def cascade_handler(self, event):
        self.context.trigger('event1')

    def cascade_async_handler(self, event):
        self.context.trigger('event1')

    def cleanup(self):
        self.clean = True


class WrongHook(Hook):
    def __init__(self, parameters):
        super(WrongHook, self).__init__(parameters)
        self.clean = False
        self.error_handler_called = False
        self.error_async_handler_called = threading.Event()
        self.context.subscribe('error_event', self.error_handler)
        self.context.subscribe('async_error_event', self.error_async_handler)

    def error_handler(self, event):
        self.error_handler_called = True
        raise Exception("BOOM!")

    def error_async_handler(self, event):
        self.error_async_handler_called.set()
        raise Exception("BOOM!")

    def cleanup(self):
        self.clean = True
        raise KeyError("Whops!")


class WrongContext(Context):
    def __init__(self, identifier):
        super(WrongContext, self).__init__(identifier)
        self.clean = False

    def cleanup(self):
        self.clean = True
        raise KeyError("Whops!")
