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

import logging
import Queue

from nrf_observers  import NrfDriverObserver
from nrf_driver     import NrfDriver
from nrf_event      import *
from nrf_event_sync import EventSync
from exceptions     import NordicSemiException

logger = logging.getLogger(__name__)

# TODO:
# - Need a reset function (should be called on close?). Is there any? softdevice disable?
# - Stuff like le_version_get and get_le_supported_features probably belongs here.


class NrfAdapter(NrfDriverObserver):

    def __init__(self, driver):
        super(NrfAdapter, self).__init__()
        self.conn_handles   = []
        self.observers      = []
        self.driver         = driver
        self.driver.observer_register(self)

    @classmethod
    def open_serial(cls, serial_port, baud_rate, ble_enable_params=None):
        adapter = cls(NrfDriver(serial_port=serial_port, baud_rate=baud_rate))
        adapter.open(ble_enable_params)
        return adapter

    def open(self, ble_enable_params=None):
        self.driver.open()
        self.driver.ble_enable(ble_enable_params)

    def close(self):
        with EventSync(self.driver, GapEvtDisconnected) as evt_sync:
            for conn_handle in self.conn_handles[:]:
                try:
                    logger.info('BLE: Disconnecting conn_handle %r', conn_handle)
                    self.driver.ble_gap_disconnect(conn_handle)
                    evt_sync.get(timeout=1.2) # TODO: If we know the conn_params we can be more informed about timeout
                except NordicSemiException:
                    logger.exception("Failed to close connections")
        self.driver.observer_unregister(self)
        self.driver.close()

    def scan_start(self, scan_params=None):
        return self.driver.ble_gap_scan_start(scan_params)

    def scan_stop(self):
        return self.driver.ble_gap_scan_stop()

    # TODO: Finish and test
    def att_mtu_exchange(self, conn_handle):
        self.driver.ble_gattc_exchange_mtu_req(conn_handle)
        #response = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_exchange_mtu_rsp)
        #return self.db_conns[conn_handle].att_mtu


    def on_driver_event(self, nrf_driver, event):
        if   isinstance(event, GapEvtConnected):
            self.conn_handles.append(event.conn_handle)

            for obs in self.observers[:]:
                obs.on_adapter(self, event)
            for obs in self.observers[:]:
                obs.on_gap_evt_connected(self, event)
        elif isinstance(event, GapEvtDisconnected):
            try:
                self.conn_handles.remove(event.conn_handle)
            except ValueError:
                pass

            for obs in self.observers[:]:
                obs.on_adapter(self, event)
            for obs in self.observers[:]:
                obs.on_gap_evt_disconnected(self, event)
        elif isinstance(event, GapEvtTimeout):
            for obs in self.observers[:]:
                obs.on_adapter(self, event)
            for obs in self.observers[:]:
                obs.on_gap_evt_timeout(self, event)
        elif isinstance(event, GapEvtAdvReport):
            for obs in self.observers[:]:
                obs.on_adapter(self, event)
            for obs in self.observers[:]:
                obs.on_gap_evt_adv_report(self, event)

    def observer_register(self, observer):
        self.observers.append(observer)

    def observer_unregister(self, observer):
        self.observers.remove(observer)
