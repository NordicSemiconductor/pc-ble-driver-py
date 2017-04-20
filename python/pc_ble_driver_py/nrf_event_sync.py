#
# Copyright (c) 2016 Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
#   3. Neither the name of Nordic Semiconductor ASA nor the names of other
#   contributors to this software may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#   4. This software must only be used in or with a processor manufactured by Nordic
#   Semiconductor ASA, or in or with a processor manufactured by a third party that
#   is used in combination with a processor manufactured by Nordic Semiconductor.
#
#   5. Any software provided in binary or object form under this license must not be
#   reverse engineered, decompiled, modified and/or disassembled.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import Queue
import time
import threading

from nrf_driver     import NrfDriver
from nrf_observers  import NrfDriverObserver


class EventSync(NrfDriverObserver):
    """Register an observer to synchronize waiting for events

    This class is used for serial code to start a procedure and wait for the resonse.

    The class takes both a list of classes to filter and a callback filter function.
    * The class filter is useful for instance to only receive GattcEvtHvx.
    * The callback filter is useful for instance to make sure that the GattcEvtHvx
      class is only for a given attribute handle.
    """
    def __init__(self, driver, event_filter=None, callback=None):
        super(NrfDriverObserver, self).__init__()

        if isinstance(driver, NrfDriver):
            self.driver     = driver
        elif hasattr(driver, "driver"):
            self.driver     = driver.driver
        else:
            raise Exception("EventSync not initialized with a driver: %s" % driver)

        if isinstance(event_filter, (list, tuple)):
            self._events    = event_filter
        elif event_filter is not None:
            self._events    = [event_filter]
        else:
            self._events    = None
        self._callback      = callback
        self._queue         = Queue.Queue() # TODO: Should not be unbound (set some size limit)

    def _isinstance_of_event(self, event):
        if self._events == None:
            return True
        for _class in self._events:
            if isinstance(event, _class):
                return True
        return False

    def on_driver_event(self, nrf_driver, event):
        if self._callback and self._callback(event):
            return # Event handled by callback
        if not self._isinstance_of_event(event):
            return
        self._queue.put(event)

    def get(self, block=True, timeout=1):
        try:
            return self._queue.get(block, timeout)
        except Queue.Empty:
            pass

    def register_as_observer(self):
        self.driver.observer_register(self)

    def unregister_as_observer(self):
        self.driver.observer_unregister(self)

    def __enter__(self):
        self.register_as_observer()
        return self

    def __exit__(self, type, value, traceback):
        self.unregister_as_observer()


class ProcedureSync(object):
    """Give serial code a chance to sync with long-running procedures.

    The procedure sync serves two purposes:
    * Make it possible for serial code to wait for procedures that can take time to finish
      * Connect request
      * Multi step procedures like pairing and service discovery
    * Give multi step procedures a state to know what the next step is when receiving an event
    """
    def __init__(self):
        self.event  = threading.Event()
        self.status = None
        self.result = []
        self._state = {}

    def wait(self, timeout=None):
        self.event.wait(timeout)
        return self


