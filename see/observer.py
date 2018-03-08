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

import logging
from threading import RLock, Thread
from collections import defaultdict, namedtuple

from see.events import Event


class Observatory(object):
    """
    Base class for observers and observables.
    """
    def __init__(self, identifier):
        self._identifier = identifier

    @property
    def identifier(self):
        return self._identifier


class Observer(Observatory):
    """The observer is the entity listening for events.

    Through the Context attribute it can subscribe/unsubscribe its own handlers
    to the given Events.
    """
    def __init__(self, identifier, context):
        super(Observer, self).__init__(identifier)
        self._context = context

    @property
    def context(self):
        return self._context


class Observable(Observatory):
    def __init__(self, identifier):
        super(Observable, self).__init__(identifier)
        self._handlers = Handlers(defaultdict(list), defaultdict(list), RLock())

    def subscribe(self, event, handler):
        """
        Subscribes a Handler for the given Event.

        @param event: (str|see.Event) event to react to.
        @param handler: (callable) function or method to subscribe.
        """
        self._handlers.sync_handlers[event].append(handler)

    def subscribe_async(self, event, handler):
        """
        Subscribes an asynchronous Handler for the given Event.

        An asynchronous handler is executed concurrently to the others
        without blocking the Events flow.

        @param event: (str|see.Event) event to react to.
        @param handler: (callable) function or method to subscribe.
        """
        self._handlers.async_handlers[event].append(handler)

    def unsubscribe(self, event, handler):
        """
        Unsubscribes the Handler from the given Event.
        Both synchronous and asynchronous handlers are removed.

        @param event: (str|see.Event) event to which the handler is subscribed.
        @param handler: (callable) function or method to unsubscribe.
        """
        try:
            self._handlers.sync_handlers[event].remove(handler)
        except ValueError:
            self._handlers.async_handlers[event].remove(handler)
        else:
            try:
                self._handlers.async_handlers[event].remove(handler)
            except ValueError:
                pass

    def trigger(self, event, **kwargs):
        """
        Triggers an event.

        All subscribed handlers will be executed, asynchronous ones
        won't block this call.

        @param event: (str|see.Event) event intended to be raised.
        """
        with self._handlers.trigger_mutex:
            event = prime_event(event, self.__class__.__name__, **kwargs)

            for handler in self._handlers.async_handlers[event]:
                asynchronous(handler, event)
            for handler in self._handlers.sync_handlers[event]:
                synchronous(handler, event)


Handlers = namedtuple('Handlers', ('sync_handlers',
                                   'async_handlers',
                                   'trigger_mutex'))


def prime_event(event, source, **kwargs):
    """
    Returns the event ready to be triggered.

    If the given event is a string an Event instance is generated from it.
    """
    if not isinstance(event, Event):
        event = Event(event, source=source, **kwargs)

    return event


def asynchronous(function, event):
    """
    Runs the function asynchronously taking care of exceptions.
    """
    thread = Thread(target=synchronous, args=(function, event))
    thread.daemon = True
    thread.start()


def synchronous(function, event):
    """
    Runs the function synchronously taking care of exceptions.
    """
    try:
        function(event)
    except Exception as error:
        logger = get_function_logger(function)
        logger.exception(error)


def get_function_logger(function):
    if hasattr(function, '__self__'):
        return logging.getLogger(
            "%s.%s" % (function.__module__,
                       function.__self__.__class__.__name__))
    else:
        return logging.getLogger(function.__module__)
