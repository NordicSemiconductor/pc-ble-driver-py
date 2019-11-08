#
# Copyright (c) 2019 Nordic Semiconductor ASA
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


import unittest
from queue import Queue, Empty
import time
import random
import string
import logging

from pc_ble_driver_py.observers import BLEDriverObserver, BLEAdapterObserver
from driver_setup import Settings, setup_adapter

from pc_ble_driver_py.ble_driver import (
    BLEDriver,
    BLEEnableParams,
    BLEConfig,
    BLEConfigConnGatt,
    BLEAdvData,
    BLEUUID,
    BLEGATTSCHARMD,
    BLEGATTSATTRMD,
    BLEGATTSATTR,
    BLEGATTSCHARHANDLES,
    BLEGATTSHVXPARAMS,
    BLEGapScanParams,
    driver,
    util,
)

logger = logging.getLogger(__name__)

class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info(
            "Central adapter is %d", self.adapter.driver.rpc_adapter.internal
        )
        self.conn_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.conn_handle = None

    def open(self):
        self.adapter.driver.open()
        gatt_cfg = BLEConfigConnGatt()
        gatt_cfg.att_mtu = self.adapter.default_mtu
        gatt_cfg.tag = 1
        self.adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
        self.adapter.driver.ble_enable()
    
    def stop(self):
        if self.conn_handle:
            self.adapter.driver.ble_gap_disconnect(self.conn_handle)

    def start(self, connect_with):
        self.connect_with = connect_with
        logger.info(f"scan_start, trying to find {self.connect_with}")
        scan_duration = 5
        #params = BLEGapScanParams(interval_ms=200, window_ms=150, timeout_s=scan_duration)
        self.adapter.driver.ble_gap_scan_start()#scan_params=params) 
        try:
            self.conn_handle = self.conn_q.get(timeout=scan_duration)
            self.adapter.service_discovery(self.conn_handle)

            #self.adapter.enable_notification(
            #    self.conn_handle, BLEUUID(BLEUUID.Standard.battery_level)
            #)

            self.adapter.enable_notification(self.conn_handle, BLEUUID(BLEUUID.Standard.heart_rate))
            logger.info(f"Found new handle: {self.conn_handle}")
        except Empty:
            logger.info(f"No heart rate collector advertising with name {self.connect_with} found.")

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)
        logger.info(f"New connection: {conn_handle}")

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        logger.info(f"Disconnected: {conn_handle} {reason}")

    def on_gap_evt_adv_report(
        self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data
    ):
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[
                BLEAdvData.Types.complete_local_name
            ]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return

        dev_name = "".join(chr(e) for e in dev_name_list)

        if dev_name == self.connect_with:
            address_string = "".join(
                "{0:02X}".format(b) for b in peer_addr.addr
            )
            logger.info(
                "Trying to connect to peripheral advertising as %s, address: 0x%s",
                dev_name,
                address_string,
            )
            self.adapter.connect(peer_addr, tag=1)

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        if len(data) > 32:
            data = f"({data[0:10]}...)"
        logger.info(f"Connection: {conn_handle}, {uuid} = {data}")

class Peripheral(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info(
            "Peripheral adapter is %d",
            self.adapter.driver.rpc_adapter.internal,
        )
        self.conn_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)


    def start(self, adv_name):
        adv_data = BLEAdvData(complete_local_name=adv_name)
        self.adapter.driver.ble_gap_adv_data_set(adv_data)
        handle_buffer = driver.new_uint16()
        serv_uuid = BLEUUID(0x180D)
        char_uuid = BLEUUID(BLEUUID.Standard.heart_rate)
        char_md = BLEGATTSCHARMD()
        attr_md = BLEGATTSATTRMD()
        char_handles = BLEGATTSCHARHANDLES()
        #init_len, max_len, value ???
        attr = BLEGATTSATTR(uuid=char_uuid.to_c(), attr_md=attr_md.to_c(), init_len=2, init_offs=0, max_len=8, value=5)
        self.adapter.driver.ble_gatts_service_add(driver.BLE_GATTS_SRVC_TYPE_PRIMARY, serv_uuid, handle_buffer)
        self.adapter.driver.ble_gatts_characteristic_add(driver.uint16_value(handle_buffer), char_md.to_c(), attr.to_c(), char_handles.to_c())
        self.adapter.driver.ble_gap_adv_start()

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)
        print('New per handle', conn_handle)

    def get_heart_rate(self):
        return random.randint(60,200)

    def sendHeartRate(self):
        length = driver.new_uint16()
        driver.uint16_assign(length, 1)
        data = driver.new_uint8()#util.list_to_uint8_array([1, 0, 1, 0, 0, 0, 1, 0])#
        driver.uint8_assign(data, 1)
        hvx_params = BLEGATTSHVXPARAMS(length=length, data=data)
        print("got params")
        breakpoint()
        res = self.adapter.driver.ble_gatts_hvx(self.conn_q.get(timeout=2), hvx_params.to_c())
        print('res', res)


class HeartRate(unittest.TestCase):

    def setUp(self):
        settings = Settings.current()

        central = setup_adapter(
            settings.serial_ports[0],
            False,
            settings.baud_rate,
            settings.retransmission_interval,
            settings.response_timeout,
            settings.driver_log_level,
        )

        self.central = Central(central)

        peripheral = setup_adapter(
            settings.serial_ports[1],
            False,
            settings.baud_rate,
            settings.retransmission_interval,
            settings.response_timeout,
            settings.driver_log_level,
        )

        # Advertising name used by peripheral and central
        # to find peripheral and connect with it
        self.adv_name = "".join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(20)
        )
        self.peripheral = Peripheral(peripheral)

    def test_rssi(self):
        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name)

        print("Send heartrate")
        try:
            self.peripheral.sendHeartRate()
        except:
            print('Exception')
        print("Sent")
        self.central.stop()

    def tearDown(self):
        self.central.adapter.close()
        self.peripheral.adapter.close()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        level=Settings.current().log_level,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    unittest.main(argv=Settings.clean_args())
