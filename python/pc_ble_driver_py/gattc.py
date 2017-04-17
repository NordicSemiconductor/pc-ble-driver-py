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

from nrf_event      import *
from nrf_types      import *
from observers      import NrfDriverObserver
from nrf_event_sync import EventSync, ProcedureSync
from gatt_db        import GattDb

logger = logging.getLogger(__name__)


# TODO:
# * Should client use EventSync or be fully interrupt driven?
#   - Opinion: service_discovery should be interrupt driven at least.
# * Keep copy of discovered database
# * More events and commands needed


class GattClient(NrfDriverObserver):

    def __init__(self, driver, peer_addr):
        super(GattClient, self).__init__()

        if hasattr(driver, "driver"):
            self.driver         = driver.driver
        else:
            self.driver         = driver

        self.peer_addr          = peer_addr
        self.conn_params        = None
        self.own_addr           = None
        self.conn_handle        = None
        self.key_set            = None

        self.observers          = []
        self.peer_db            = GattDb()
        self._connect_sync      = None
        self._prim_src_disc     = None
        self._char_disc         = None
        self._desc_disc         = None

        self.observer_register(self.peer_db)
        self.driver.observer_register(self)

    def __del__(self):
        self.driver.observer_unregister(self)

    def observer_register(self, observer):
        self.observers.append(observer)

    def observer_unregister(self, observer):
        self.observers.remove(observer)

    # gap

    def connect(self, scan_params=None, conn_params=None):
        if scan_params is None:
            scan_params = self.driver.scan_params_setup()
        if conn_params is None:
            conn_params = self.driver.conn_params_setup()
        self.conn_params = conn_params
        self._connect_sync = ProcedureSync()
        self.driver.ble_gap_connect(self.peer_addr, conn_params=conn_params)
        return self._connect_sync

    def disconnect(self, hci_status_code=BLEHci.remote_user_terminated_connection):
        with EventSync(self.driver, GapEvtDisconnected) as evt_sync:
            self.driver.ble_gap_disconnect(self.conn_handle, hci_status_code)
            event = evt_sync.get(self.conn_params.conn_sup_timeout_ms / 1000.)

    def gap_authenticate(self, sec_params):
        self.driver.ble_gap_authenticate(self.conn_handle, sec_params)


    # gattc

    def read(self, attr_handle):
        with EventSync(self.driver, GattcEvtReadResponse) as evt_sync:
            self.driver.ble_gattc_read(self.conn_handle, attr_handle)
            return evt_sync.get()

    def write(self, attr_handle, value, offset=0):
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           attr_handle,
                                           value,
                                           offset)
        with EventSync(self.driver, GattcEvtWriteResponse) as evt_sync:
            self.driver.ble_gattc_write(self.conn_handle, write_params)
            event = evt_sync.get()
            if event is None:
                logger.error('Did not receive GattcEvtWriteResponse event')
            return event

    def write_cmd(self, attr_handle, value, offset=0):
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_cmd,
                                           BLEGattExecWriteFlag.unused,
                                           attr_handle,
                                           value,
                                           offset)
        with EventSync(self.driver, EvtTxComplete) as evt_sync:
            self.driver.ble_gattc_write(self.conn_handle, write_params)
            event = evt_sync.get()
            if event is None:
                logger.error('Did not receive EvtTxComplete event')
            return event

    def enable_notification(self, cccd_handle, on=True, indication=False):
        if on:
            if indication:
                value =[0x02, 0x00]
            else:
                value = [0x01, 0x00]
        else:
            value = [0x00, 0x00]
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           cccd_handle,
                                           value,
                                           0)
        with EventSync(self.driver, GattcEvtWriteResponse) as evt_sync:
            self.driver.ble_gattc_write(self.conn_handle, write_params)
            event = evt_sync.get()
            if event is None:
                logger.error('Did not receive HciNumCompletePackets event')
            return event

    def primary_service_discovery(self, uuid=None):
        if self._prim_src_disc is not None:
            # TODO: How to handle? raise exception? return ongoing? what?
            pass

        self._prim_src_disc = ProcedureSync()
        self._prim_src_disc._state = {'uuid': uuid, 'type': 'prim_srvc_disc'}
        self.driver.ble_gattc_prim_srvc_disc(self.conn_handle, self._prim_src_disc._state['uuid'], 0x0001)
        return self._prim_src_disc

    def _handle_primary_service_discovery_response(self, event):
        # Stop processing if we are not doing event driven service discovery
        if self._prim_src_disc is None:
            return

        if event.status == BLEGattStatusCode.attribute_not_found:
            self._prim_src_disc.status = BLEGattStatusCode.success # TODO: We are done, right?
            self._prim_src_disc.event.set()
            self._prim_src_disc = None
            return
        elif event.status != BLEGattStatusCode.success:
            self._prim_src_disc.status = event.status
            self._prim_src_disc.event.set()
            self._prim_src_disc = None
            return

        self._prim_src_disc.result.extend(event.services)

        if event.services[-1].end_handle == 0xFFFF:
            self._prim_src_disc.status = BLEGattStatusCode.success
            self._prim_src_disc.event.set()
            self._prim_src_disc = None
            return

        self.driver.ble_gattc_prim_srvc_disc(self.conn_handle, self._prim_src_disc._state['uuid'], event.services[-1].end_handle + 1)

    def characteristics_discovery(self, service):
        if self._char_disc is not None:
            # TODO: How to handle? raise exception? return ongoing? what?
            pass

        self._char_disc = ProcedureSync()
        self._char_disc._state = {'service': service, 'type': 'char_disc'}
        self.driver.ble_gattc_char_disc(self.conn_handle, service.start_handle, service.end_handle)
        return self._char_disc

    def _handle_characteristic_discovery_response(self, event):
        # Stop processing if we are not doing event driven characteristic discovery
        if self._char_disc is None:
            return

        service = self._char_disc._state['service']

        if event.status == BLEGattStatusCode.attribute_not_found:
            self._char_disc.status = BLEGattStatusCode.success
            self._char_disc.event.set()
            self._char_disc = None
            return
        elif event.status != BLEGattStatusCode.success:
            self._char_disc.status = event.status
            self._char_disc.event.set()
            self._char_disc = None
            return

        for char in event.characteristics:
            service.char_add(char)
        self._char_disc.result.extend(event.characteristics)

        last_char = event.characteristics[-1]
        if last_char.handle_value == service.end_handle:
            self._char_disc.status = BLEGattStatusCode.success
            self._char_disc.event.set()
            self._char_disc = None
            return

        self.driver.ble_gattc_char_disc(self.conn_handle, last_char.handle_decl + 1, service.end_handle)

    def descriptor_discovery(self, char):
        if self._desc_disc is not None:
            # TODO: How to handle? raise exception? return ongoing? what?
            pass

        self._desc_disc = ProcedureSync()
        self._desc_disc._state = {'char': char, 'type': 'desc_disc'}
        self.driver.ble_gattc_desc_disc(self.conn_handle, char.handle_value + 1, char.end_handle)
        return self._desc_disc

    def _handle_descriptor_discovery_response(self, event):
        # Stop processing if we are not doing event driven descriptor discovery
        if self._desc_disc is None:
            return

        if event.status == BLEGattStatusCode.attribute_not_found:
            self._desc_disc.status = BLEGattStatusCode.success
            self._desc_disc.event.set()
            self._desc_disc = None
            return
        elif event.status != BLEGattStatusCode.success:
            self._desc_disc.status = BLEGattStatusCode.success
            self._desc_disc.event.set()
            self._desc_disc = None
            return

        char = self._desc_disc._state['char']
        char.descs.extend(event.descriptions)
        self._desc_disc.result.extend(event.descriptions)

        last_descr = event.descriptions[-1]
        if last_descr.handle == char.end_handle:
            self._desc_disc.status = BLEGattStatusCode.success
            self._desc_disc.event.set()
            self._desc_disc = None
            return

        self.driver.ble_gattc_desc_disc(self.conn_handle, last_descr.handle + 1, char.end_handle)

    # TODO: Blocking call (is this ok). Needs a bit of testing
    def get_peer_db(self, proc_timeout=10):
        proc_sync = self.primary_service_discovery()
        proc_sync.wait(proc_timeout)
        if proc_sync.status != BLEGattStatusCode.success:
            return

        services = proc_sync.result
        for service in services:
            proc_sync = self.characteristics_discovery(service)
            proc_sync.wait(proc_timeout)
            if proc_sync.status != BLEGattStatusCode.success:
                return

            for char in service.chars:
                read = self.read(char.handle_decl)
                if read is None:
                    return
                char.data_decl = read.data

                read = self.read(char.handle_value)
                if read is None:
                    return
                char.data_value = read.data

                proc_sync = self.descriptor_discovery(char)
                proc_sync.wait(proc_timeout)
                if proc_sync.status != BLEGattStatusCode.success:
                    return
                for descr in char.descs:
                    read = self.read(descr.handle)
                    if read is None:
                        return
                    descr.data = read.data

        return services

    def on_driver_event(self, nrf_driver, event):
        #print event

        # gap

        if   isinstance(event, GapEvtConnected):
            if event.peer_addr != self.peer_addr:
                return # Filter out events for other links
            self.conn_handle        = event.conn_handle
            self.own_addr           = event.own_addr

            self._connect_sync.status = True # TODO: Maybe BLE_GAP_EVT_CONNECTED?
            self._connect_sync.event.set()
            self._connect_sync = None

            for obs in self.observers[:]:
                obs.on_gattc_event(self, event)
            for obs in self.observers[:]:
                obs.on_connected(self, event)
            return
        elif isinstance(event, GapEvtTimeout):
            if event.src != BLEGapTimeoutSrc.conn:
                return
            if not self._connect_sync:
                return

            self._connect_sync.status = False # TODO: Maybe BLE_GAP_EVT_TIMEOUT?
            self._connect_sync.event.set()
            self._connect_sync = None

            for obs in self.observers[:]:
                obs.on_gattc_event(self, event)
            return
        elif event.conn_handle != self.conn_handle:
            return # Filter out events for other links

        for obs in self.observers[:]:
            obs.on_gattc_event(self, event)

        if   isinstance(event, GapEvtDisconnected):
            for obs in self.observers[:]:
                obs.on_disconnected(self, event)

            self.conn_handle        = None
            self.own_addr           = None
        elif isinstance(event, GapEvtConnParamUpdateRequest):
            for obs in self.observers[:]:
                obs.on_connection_param_update_request(self, event)
        elif isinstance(event, GapEvtConnParamUpdate):
            for obs in self.observers[:]:
                obs.on_connection_param_update(self, event)
        elif isinstance(event, GapEvtSecParamsRequest):
            for obs in self.observers[:]:
                obs.on_sec_params_request(self, event)
        elif isinstance(event, GapEvtAuthKeyRequest):
            for obs in self.observers[:]:
                obs.on_auth_key_request(self, event)
        elif isinstance(event, GapEvtConnSecUpdate):
            for obs in self.observers[:]:
                obs.on_conn_sec_update(self, event)
        elif isinstance(event, GapEvtAuthStatus):
            for obs in self.observers[:]:
                obs.on_auth_status(self, event)

        # gattc

        elif isinstance(event, GattcEvtPrimaryServicecDiscoveryResponse):
            for obs in self.observers[:]:
                obs.on_primary_service_discovery_response(self, event)
            self._handle_primary_service_discovery_response(event)
        elif isinstance(event, GattcEvtCharacteristicDiscoveryResponse):
            for obs in self.observers[:]:
                obs.on_characteristic_discovery_response(self, event)
            self._handle_characteristic_discovery_response(event)
        elif isinstance(event, GattcEvtDescriptorDiscoveryResponse):
            for obs in self.observers[:]:
                obs.on_descriptor_discovery_response(self, event)
            self._handle_descriptor_discovery_response(event)
        elif isinstance(event, GattcEvtHvx):
            is_notification = event.hvx_type == BLEGattHVXType.notification
            is_indication   = event.hvx_type == BLEGattHVXType.indication
            for obs in self.observers[:]:
                if is_notification:
                    obs.on_notification(self, event)
                if is_indication:
                    obs.on_indication(self, event)
