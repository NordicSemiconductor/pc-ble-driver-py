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

from pc_ble_driver_py.observers     import *

TARGET_DEV_NAME = "Nordic_HRM"
CONNECTIONS     = 1

def init(conn_ic_id):
    global BLEDriver, BLEAdvData, BLEEvtID, BLEAdapter, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID
    from pc_ble_driver_py import config
    config.__conn_ic_id__ = conn_ic_id
    from pc_ble_driver_py.ble_driver    import BLEDriver, BLEAdvData, BLEEvtID, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID
    from pc_ble_driver_py.ble_adapter   import BLEAdapter
    global nrf_sd_ble_api_ver
    nrf_sd_ble_api_ver = config.sd_api_ver_get()

class HRCollector(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        super(HRCollector, self).__init__()
        self.adapter    = adapter
        self.conn_q     = Queue.Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)


    def open(self):
        self.adapter.driver.open()

        ble_enable_params = BLEEnableParams(vs_uuid_count      = 1,
                                            service_changed    = False,
                                            periph_conn_count  = 0,
                                            central_conn_count = CONNECTIONS,
                                            central_sec_count  = CONNECTIONS)
        if nrf_sd_ble_api_ver >= 3:
            print("Enabling larger ATT MTUs")
            ble_enable_params.att_mtu = 50

        self.adapter.driver.ble_enable(ble_enable_params)


    def close(self):
        self.adapter.driver.close()


    def connect_and_discover(self):
        self.adapter.driver.ble_gap_scan_start()
        new_conn = self.conn_q.get(timeout = 60)

        if nrf_sd_ble_api_ver >= 3:
            att_mtu = self.adapter.att_mtu_exchange(new_conn)

        self.adapter.service_discovery(new_conn)
        self.adapter.enable_notification(new_conn, BLEUUID(BLEUUID.Standard.battery_level))
        self.adapter.enable_notification(new_conn, BLEUUID(BLEUUID.Standard.heart_rate))
        return new_conn


    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        print('New connection: {}'.format(conn_handle))
        self.conn_q.put(conn_handle)


    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        print('Disconnected: {} {}'.format(conn_handle, reason))


    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        if src == BLEGapTimeoutSrc.scan:
            ble_driver.ble_gap_scan_start()


    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        dev_name_list = None
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]

        else:
            return

        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        print('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                    dev_name))

        if (dev_name == TARGET_DEV_NAME):
            self.adapter.connect(peer_addr)


    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        print('Connection: {}, {} = {}'.format(conn_handle, uuid, data))


    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        print('ATT MTU exchanged: conn_handle={} att_mtu={}'.format(conn_handle, att_mtu))


    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
        print('ATT MTU exchange response: conn_handle={}'.format(conn_handle))
    

def main(serial_port):
    print('Serial port used: {}'.format(serial_port))
    driver    = BLEDriver(serial_port=serial_port, auto_flash=True)
    adapter   = BLEAdapter(driver)
    collector = HRCollector(adapter)
    collector.open()
    for i in xrange(CONNECTIONS):
        conn_handle = collector.connect_and_discover()

    time.sleep(30)
    print('Closing')
    collector.close()


def item_choose(item_list):
    for i, it in enumerate(item_list):
        print('\t{} : {}'.format(i, it))
    print(' ')

    while True:
        try:
            choice = int(raw_input('Enter your choice: '))
            if ((choice >= 0) and (choice < len(item_list))):
                break
        except Exception:
            pass
        print ('\tTry again...')
    return choice


if __name__ == "__main__":
    serial_port = None
    if len(sys.argv) < 2:
        print("Please specify connectivity IC identifier (NRF51, NRF52)")
        exit(1)
    init(sys.argv[1])
    if len(sys.argv) == 3:
        serial_port = sys.argv[2]
    else:
        descs       = BLEDriver.enum_serial_ports()
        choices     = ['{}: {}'.format(d.port, d.serial_number) for d in descs]
        choice      = item_choose(choices)
        serial_port = descs[choice].port
    main(serial_port)
    quit()
