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

import sys
import time
import Queue
import logging
import traceback

from pc_ble_driver_py.observers import NrfAdapterObserver, GattClientObserver
from pc_ble_driver_py.exceptions import NordicSemiException

TARGET_DEV_NAME = "Nordic_HRM"
CONNECTIONS     = 1

def logger_setup():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logging.getLogger().addHandler(sh)
    return logger


def init(conn_ic_id):
    global logger, config, nrf_types, nrf_event, NrfAdapter, BLEDevice
    logger = logger_setup()

    from pc_ble_driver_py import config
    config.set_conn_ic(conn_ic_id)

    from pc_ble_driver_py               import nrf_types
    from pc_ble_driver_py               import nrf_event
    from pc_ble_driver_py.nrf_adapter   import NrfAdapter
    from pc_ble_driver_py.ble_device    import BLEDevice

class HRCollector(NrfAdapterObserver, GattClientObserver):
    def __init__(self, adapter):
        super(HRCollector, self).__init__()
        self.adapter    = adapter
        self.device     = BLEDevice(self.adapter.driver, None)
        self.adapter.observer_register(self)

    def connect_and_discover(self):
        self.adapter.scan_start()

        if not self.device.connected.wait(10):
            raise NordicSemiException('Timeout. Device not found.')

        self.device.gattc.observer_register(self)

        if config.sd_api_ver_get() >= 3:
            att_mtu = self.adapter.att_mtu_exchange(self.device.conn_handle)

        services = self.get_peer_db()

        if not services:
            print("Peer database discovery failed")
            return

        self.print_peer_db(services)

        for service in services:
            for char in service.chars:
                if not char.uuid.get_value() == nrf_types.BLEUUID.Standard.heart_rate.value:
                    continue
                for descr in char.descs:
                    if descr.uuid.get_value() == nrf_types.BLEUUID.Standard.cccd.value:
                        self.device.gattc.enable_notification(descr.handle)

    def get_peer_db(self):
        proc_sync = self.device.gattc.primary_service_discovery()
        proc_sync.wait(8)
        if proc_sync.status != nrf_types.BLEGattStatusCode.success:
            return

        services = proc_sync.result
        for service in services:
            proc_sync = self.device.gattc.characteristics_discovery(service)
            proc_sync.wait(8)
            if proc_sync.status != nrf_types.BLEGattStatusCode.success:
                return

            for char in service.chars:
                read = self.device.gattc.read(char.handle_decl)
                if read is None:
                    return
                char.data_decl = read.data

                read = self.device.gattc.read(char.handle_value)
                if read is None:
                    return
                char.data_value = read.data

                proc_sync = self.device.gattc.descriptor_discovery(char)
                proc_sync.wait(8)
                if proc_sync.status != nrf_types.BLEGattStatusCode.success:
                    return
                for descr in char.descs:
                    read = self.device.gattc.read(descr.handle)
                    if read is None:
                        return
                    descr.data = read.data

        return services

    def print_peer_db(self, services):
        for service in services:
            logger.info(        '  0x%04x         0x%04x   -- %s', service.start_handle, service.srvc_uuid.get_value(), service.uuid)
            for char in service.chars:
                logger.info(    '    0x%04x       0x%04x   --   %r', char.handle_decl, char.char_uuid.get_value(), ''.join(map(chr, char.data_decl)))
                logger.info(    '      0x%04x     0x%04x   --     %r', char.handle_value, char.uuid.get_value(), ''.join(map(chr, char.data_value)))
                for descr in char.descs:
                    logger.info('      0x%04x     0x%04x   --     %r', descr.handle, descr.uuid.get_value(), ''.join(map(chr, descr.data)))

    def on_gap_evt_adv_report(self, adapter, event):
        dev_name_list = None
        if nrf_types.BLEAdvData.Types.complete_local_name in event.adv_data.records:
            dev_name_list = event.adv_data.records[nrf_types.BLEAdvData.Types.complete_local_name]
        elif nrf_types.BLEAdvData.Types.short_local_name in event.adv_data.records:
            dev_name_list = event.adv_data.records[nrf_types.BLEAdvData.Types.short_local_name]
        else:
            return

        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in event.peer_addr.addr)
        print('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                    dev_name))

        if (dev_name == TARGET_DEV_NAME):
            self.device.peer_addr = event.peer_addr
            self.device.connect()

    def on_notification(self, gatt_client, event):
        print('Connection: {}, {} = {}'.format(event.conn_handle, event.attr_handle, event.data))


    #def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
    #    print('ATT MTU exchanged: conn_handle={} att_mtu={}'.format(conn_handle, att_mtu))


    #def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
    #    print('ATT MTU exchange response: conn_handle={}'.format(conn_handle))


def main(serial_port, baud_rate):
    print('Serial port used: {}'.format(serial_port))
    ble_enable_params = nrf_types.BLEEnableParams(
            vs_uuid_count       = 1, service_changed    = False,
            periph_conn_count   = 0, central_conn_count = CONNECTIONS,
            central_sec_count   = CONNECTIONS)

    if config.sd_api_ver_get() >= 3:
        print("Enabling larger ATT MTUs")
        ble_enable_params.att_mtu = 50

    adapter = None
    try:
        adapter   = NrfAdapter.open_serial(serial_port, baud_rate, ble_enable_params)
        collector = HRCollector(adapter)
        for i in xrange(CONNECTIONS):
            collector.connect_and_discover()

        time.sleep(10)
    except:
        traceback.print_exc()
    if adapter:
        print("Closing")
        adapter.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Please specify connectivity IC identifier (NRF51, NRF52) and port (COMx)")
        exit(1)

    baud_rate = None
    if len(sys.argv) == 4:
        baud_rate = int(sys.argv[3])

    init(sys.argv[1])
    main(sys.argv[2], baud_rate)
    quit()
