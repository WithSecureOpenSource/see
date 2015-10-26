import unittest

from see import events
from see.observer import prime_event


class EventTest(unittest.TestCase):
    def test_event(self):
        """Event creation test."""
        event = events.Event('event', source='me', foo='bar', baz=1)
        self.assertTrue(isinstance(event, str))
        self.assertEqual(event.source, 'me')
        self.assertEqual(event.foo, 'bar')
        self.assertEqual(event.baz, 1)

    def test_event_priming(self):
        """Event priming test."""
        event = prime_event('event', 'me', foo='bar', baz=1)
        event = events.Event('event', source='me', foo='bar', baz=1)
        self.assertTrue(isinstance(event, str))
        self.assertEqual(event.source, 'me')
        self.assertEqual(event.foo, 'bar')
        self.assertEqual(event.baz, 1)
