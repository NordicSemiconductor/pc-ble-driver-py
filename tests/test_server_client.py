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

from driver_setup import Settings, setup_adapter
import logging
logger = logging.getLogger(__name__)
import random
import string
import unittest
from queue import Empty, Queue

import xmlrunner
from pc_ble_driver_py.ble_driver import (
    BLEUUID,
    BLEAdvData,
    BLEGattCharProps,
    BLEGattHandle,
    BLEGattsAttr,
    BLEGattsAttrMD,
    BLEGattsCharHandles,
    BLEGattsCharMD,
    BLEGattsHVXParams,
    BLEUUIDBase,
    driver,
)
from pc_ble_driver_py.observers import BLEAdapterObserver, BLEDriverObserver




UUID_HEART_RATE_SERVICE = 0x180D  # Heart Rate service UUID
UUID_HEART_RATE_CHAR = 0x2A37  # Heart Rate Measurement characteristic UUID
UUID_CUSTOM_SERVICE = 0x1111
UUID_CUSTOM_CHAR = 0x2222
CUSTOM_BASE = [
    0x11,
    0x22,
    0x33,
    0x44,
    0x00,
    0x00,
    0x55,
    0x66,
    0x77,
    0x88,
    0x99,
    0xAA,
    0xBB,
    0xCC,
    0xDD,
    0xEE,
]
DATA = [100]  # Heart Rate list
ATTR_VALUE = [10]  # Initial Heart Rate Measurement Packet list
ATTR_MAX_LEN = 8  # Heart Rate Measurement Packet maximum size


class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info("Central adapter is %d", self.adapter.driver.rpc_adapter.internal)
        self.conn_q = Queue()
        self.notification_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.conn_handle = None

    def stop(self):
        if self.conn_handle:
            self.adapter.driver.ble_gap_disconnect(self.conn_handle)

    def start(self, connect_with):
        self.connect_with = connect_with
        logger.info(f"scan_start, trying to find {self.connect_with}")
        scan_duration = 5
        self.adapter.driver.ble_gap_scan_start()
        try:
            self.conn_handle = self.conn_q.get(timeout=scan_duration)
            self.adapter.service_discovery(self.conn_handle)
        except Empty:
            logger.info(
                f"No peripherial advertising with name" f"{self.connect_with} found."
            )

    def enable_notification(self, uuid):
        self.adapter.enable_notification(self.conn_handle, uuid)
        logger.info(f"Notification enabled.")

    def disable_notification(self, uuid):
        self.adapter.disable_notification(self.conn_handle, uuid)
        logger.info(f"Notification disabled.")

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)
        logger.info(f"(Central) New connection: {conn_handle}.")

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        logger.info(f"Disconnected: {conn_handle} {reason}.")

    def on_gap_evt_adv_report(
        self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data
    ):
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return

        dev_name = "".join(chr(e) for e in dev_name_list)

        if dev_name == self.connect_with:
            address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
            logger.info(
                f"Trying to connect to peripheral advertising as {dev_name},"
                f" address: 0x{address_string}"
            )
            self.adapter.connect(peer_addr, tag=1)

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        logger.info(f"Connection: {conn_handle}, {uuid} = {data}.")
        self.notification_q.put(data)


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
        self.char_handles = None
        self.uuid_128_base = None

    def setup_services_16bit(self):
        self.char_handles = BLEGattsCharHandles()
        serv_handle = BLEGattHandle()
        serv_uuid = BLEUUID(UUID_HEART_RATE_SERVICE)
        char_uuid = BLEUUID(UUID_HEART_RATE_CHAR)

        props = BLEGattCharProps(notify=True)
        char_md = BLEGattsCharMD(char_props=props)
        attr_md = BLEGattsAttrMD()
        attr = BLEGattsAttr(
            uuid=char_uuid, attr_md=attr_md, max_len=ATTR_MAX_LEN, value=ATTR_VALUE
        )

        self.adapter.driver.ble_gatts_service_add(
            driver.BLE_GATTS_SRVC_TYPE_PRIMARY, serv_uuid, serv_handle
        )
        self.adapter.driver.ble_gatts_characteristic_add(
            serv_handle.handle, char_md, attr, self.char_handles
        )

    def setup_services_128bit(self):
        self.char_128_handles = BLEGattsCharHandles()
        serv_128_handle = BLEGattHandle()
        uuid_128_base = BLEUUIDBase(CUSTOM_BASE)
        serv_128_uuid = BLEUUID(UUID_CUSTOM_SERVICE, uuid_128_base)
        char_128_uuid = BLEUUID(UUID_CUSTOM_CHAR, uuid_128_base)

        props = BLEGattCharProps(notify=True)
        char_md = BLEGattsCharMD(char_props=props)
        attr_md = BLEGattsAttrMD()
        attr = BLEGattsAttr(
            uuid=char_128_uuid, attr_md=attr_md, max_len=ATTR_MAX_LEN, value=ATTR_VALUE
        )

        self.adapter.driver.ble_vs_uuid_add(uuid_128_base)
        self.adapter.driver.ble_gatts_service_add(
            driver.BLE_GATTS_SRVC_TYPE_PRIMARY, serv_128_uuid, serv_128_handle
        )
        self.adapter.driver.ble_gatts_characteristic_add(
            serv_128_handle.handle, char_md, attr, self.char_128_handles
        )

    def start(self, adv_name):
        adv_data = BLEAdvData(complete_local_name=adv_name)
        self.adapter.driver.ble_gap_adv_data_set(adv_data)
        self.adapter.driver.ble_gap_adv_start()

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)
        logger.info(f"(Peripheral) New connection: {conn_handle}.")

    def send_data(self, data):
        hvx_params = BLEGattsHVXParams(
            handle=self.char_handles,
            hvx_type=driver.BLE_GATT_HVX_NOTIFICATION,
            data=data,
        )
        self.adapter.driver.ble_gatts_hvx(self.conn_q.get(timeout=2), hvx_params)

    def send_data_128(self, data):
        hvx_params = BLEGattsHVXParams(
            handle=self.char_128_handles,
            hvx_type=driver.BLE_GATT_HVX_NOTIFICATION,
            data=data,
        )
        self.adapter.driver.ble_gatts_hvx(self.conn_q.get(timeout=2), hvx_params)


class ServerClient(unittest.TestCase):
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
            random.choice(string.ascii_uppercase + string.digits) for _ in range(20)
        )
        self.peripheral = Peripheral(peripheral)

    def test_server_client_16(self):
        self.peripheral.setup_services_16bit()
        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name)

        char_uuid = BLEUUID(UUID_HEART_RATE_CHAR)
        self.central.enable_notification(char_uuid)

        self.peripheral.send_data(DATA)
        notification = self.central.notification_q.get(timeout=5)
        self.assertTrue(notification == DATA)

        self.central.disable_notification(char_uuid)
        self.central.stop()

    def test_server_client_128(self):
        self.peripheral.setup_services_128bit()
        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name)
        uuid_128_base = BLEUUIDBase(CUSTOM_BASE)
        char_128_uuid = BLEUUID(UUID_CUSTOM_CHAR, uuid_128_base)
        self.central.enable_notification(char_128_uuid)

        self.peripheral.send_data_128(DATA)
        notification = self.central.notification_q.get(timeout=5)
        self.assertTrue(notification == DATA)

        self.central.disable_notification(char_128_uuid)
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
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(
            output=Settings.current().test_output_directory
        ),
        argv=Settings.clean_args(),
    )
