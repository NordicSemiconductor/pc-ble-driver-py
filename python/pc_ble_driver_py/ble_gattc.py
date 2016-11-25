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
from nrf_driver     import NrfDriverObserver
from nrf_event_sync import EventSync

logger = logging.getLogger(__name__)


# TODO:
# * Should client use EventSync or be fully interrupt driven?
#   - Opinion: service_discovery should be interrupt driven at least.
# * Keep copy of discovered database
# * More events and commands needed


class GattClient(NrfDriverObserver):

    def __init__(self, driver, conn_handle):
        super(GattClient, self).__init__()
        self.conn_handle    = conn_handle
        self.driver         = driver
        self.driver.observer_register(self)

    def __del__(self):
        self.driver.observer_unregister(self)

    def read(self, attr_handle):
        with EventSync(self.driver, [GattcEvtReadResponse]) as evt_sync:
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
                logger.error('Did not receive HciNumCompletePackets event')
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
                logger.error('Did not receive HciNumCompletePackets event')
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

    def service_discovery(self, uuid=None):
        classes = [GattcEvtReadResponse,
                   GattcEvtCharacteristicDiscoveryResponse,
                   GattcEvtDescriptorDiscoveryResponse]
        with EventSync(self.driver, GattcEvtPrimaryServicecDiscoveryResponse) as evt_sync:
            self.driver.ble_gattc_prim_srvc_disc(self.conn_handle, uuid, 0x0001)
            services = []
            while True:
                event = evt_sync.get()

                if isinstance(event, GattcEvtPrimaryServicecDiscoveryResponse):
                    services.extend(event.services)
                elif event.status == BLEGattStatusCode.attribute_not_found:
                    break
                else:
                    return event.status

                if event.services[-1].end_handle == 0xFFFF:
                    break
                else:
                    self.driver.ble_gattc_prim_srvc_disc(self.conn_handle, uuid, event.services[-1].end_handle + 1)

        classes = [GattcEvtReadResponse,
                   GattcEvtCharacteristicDiscoveryResponse,
                   GattcEvtDescriptorDiscoveryResponse]
        with EventSync(self.driver, classes) as evt_sync:
            for service in services:
                self.driver.ble_gattc_char_disc(self.conn_handle, service.start_handle, service.end_handle)
                while True:
                    event = evt_sync.get()

                    if event is None:
                        return # TODO: Is this correct?
                    elif event.status == BLEGattStatusCode.success:
                        map(service.char_add, event.characteristics)
                    elif event.status == BLEGattStatusCode.attribute_not_found:
                        break
                    else:
                        return event.status

                    self.driver.ble_gattc_char_disc(self.conn_handle,
                                                    event.characteristics[-1].handle_decl + 1,
                                                    service.end_handle)

                for char in service.chars:
                    self.driver.ble_gattc_desc_disc(self.conn_handle, char.handle_value, char.end_handle)
                    while True:
                        event = evt_sync.get()

                        if event is None:
                            return # TODO: Is this correct?
                        elif event.status == BLEGattStatusCode.success:
                            char.descs.extend(event.descriptions)
                        elif event.status == BLEGattStatusCode.attribute_not_found:
                            break
                        else:
                            return event.status

                        if event.descriptions[-1].handle == char.end_handle:
                            break
                        else:
                            self.driver.ble_gattc_desc_disc(self.conn_handle,
                                                            event.descriptions[-1].handle + 1,
                                                            char.end_handle)

    def on_event(self, nrf_driver, event):
        if event.conn_handle != self.conn_handle:
            # Filter out events for other links
            return
        elif isinstance(event, GapEvtConnected):
            pass #    self.conn_handles.append(event.conn_handle)
        elif isinstance(event, GapEvtDisconnected):
            pass #    self.conn_handle.remove(event.conn_handle)
        elif isinstance(event, GattcEvtPrimaryServicecDiscoveryResponse):
            for service in event.services:
                logger.debug('New service uuid: %s, start handle: %02x, end handle: %02x',
                    service.uuid, service.start_handle, service.end_handle)
        elif isinstance(event, GattcEvtDescriptorDiscoveryResponse):
            for descriptor in event.descriptions:
                logger.debug('New descriptor uuid: %s, handle: %02x', descriptor.uuid, descriptor.handle)
        elif isinstance(event, GattcEvtCharacteristicDiscoveryResponse):
            for characteristic in event.characteristics:
                logger.debug('New characteristic uuid: %s, declaration handle: %02x, value handle: %02x',
                        characteristic.uuid, characteristic.handle_decl, characteristic.handle_value)
