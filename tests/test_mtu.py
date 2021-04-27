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

import logging
import random
import string
import unittest
from queue import Queue

import xmlrunner
from pc_ble_driver_py.ble_driver import BLEAdvData
from pc_ble_driver_py.exceptions import NordicSemiException
from pc_ble_driver_py.observers import BLEAdapterObserver, BLEDriverObserver

from driver_setup import Settings, setup_adapter

logger = logging.getLogger(__name__)


class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info("Central adapter is %d", self.adapter.driver.rpc_adapter.internal)
        self.conn_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.conn_handle = None
        self.mtu_rsp = None
        self.new_mtu = None

    def start(self, connect_with, requested_mtu):
        self.connect_with = connect_with
        logger.info("scan_start, trying to find %s", self.connect_with)
        self.adapter.driver.ble_gap_scan_start()
        self.conn_handle = self.conn_q.get(timeout=5)
        self.new_mtu = self.adapter.att_mtu_exchange(self.conn_handle, requested_mtu)

    def stop(self):
        if self.conn_handle:
            self.adapter.driver.ble_gap_disconnect(self.conn_handle)

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
                "Trying to connect to peripheral advertising as %s, address: 0x%s",
                dev_name,
                address_string,
            )

            self.adapter.connect(peer_addr, tag=Settings.CFG_TAG)

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)

    # This event is handled by BLEAdapter. Included here for test inspection only.
    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
        self.mtu_rsp = kwargs["att_mtu"]


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
        self.mtu_req = None

    def start(self, adv_name):
        adv_data = BLEAdvData(complete_local_name=adv_name)
        self.adapter.driver.ble_gap_adv_data_set(adv_data)
        self.adapter.driver.ble_gap_adv_start(tag=Settings.CFG_TAG)

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)

    # This event is handled by BLEAdapter. Included here for test inspection only.
    def on_gatts_evt_exchange_mtu_request(self, ble_driver, conn_handle, client_mtu):
        self.mtu_req = client_mtu


class Mtu(unittest.TestCase):
    def setUp(self):
        settings = Settings.current()

        settings.mtu = 200

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

    def test_mtu(self):
        requested_mtu = 150
        max_supported_mtu = Settings.current().mtu

        self.assertTrue(Settings.current().mtu >= requested_mtu)

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, requested_mtu)

        self.assertEqual(self.peripheral.mtu_req, requested_mtu)
        self.assertEqual(self.central.mtu_rsp, max_supported_mtu)

        common_supported_mtu = min(max_supported_mtu, requested_mtu)
        self.assertEqual(self.central.new_mtu, common_supported_mtu)

        self.central.stop()

    def test_mtu_invalid(self):
        requested_mtu = 250

        self.assertTrue(Settings.current().mtu < requested_mtu)

        self.peripheral.start(self.adv_name)
        with self.assertRaises(NordicSemiException):
            self.central.start(self.adv_name, requested_mtu)

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
