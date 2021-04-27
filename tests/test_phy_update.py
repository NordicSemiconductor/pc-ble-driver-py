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
logger = logging.getLogger(__name__)

import random
import string
import unittest
from queue import Empty, Queue

import xmlrunner
from pc_ble_driver_py.ble_driver import BLEAdvData, BLEHci, driver
from pc_ble_driver_py.observers import BLEAdapterObserver, BLEDriverObserver

from driver_setup import Settings, setup_adapter



class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, tester, adapter):
        self.tester = tester
        self.adapter = adapter
        logger.info(f"Central adapter is {self.adapter.driver.rpc_adapter.internal}")
        self.conn_q = Queue()
        self.phy_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.conn_handle = None
        self.phy_rsp = None
        self.new_phy = None

    def stop(self):
        if self.conn_handle:
            self.adapter.driver.ble_gap_disconnect(self.conn_handle)

    def start(self, connect_with, req_phys):
        self.connect_with = connect_with
        logger.info(f"scan_start, trying to find {self.connect_with}")
        scan_duration = 5
        self.adapter.driver.ble_gap_scan_start()
        try:
            self.conn_handle = self.conn_q.get(timeout=scan_duration)
            logging.info(f"Central requesting: req_phys={req_phys}")
            resp = self.adapter.phy_update(self.conn_handle, req_phys)
            self.new_phy = resp
        except Empty:
            logger.info(
                f"No peripherial advertising with name {self.connect_with} found."
            )

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)
        logger.info(f"Central connected, conn_handle={conn_handle}.")

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        logger.info(f"Disconnected: conn_handle={conn_handle} reason={reason}.")

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
            address_string = "".join(f"{b:02X}" for b in peer_addr.addr)
            logger.info(
                f"Trying to connect to peripheral advertising as {dev_name},"
                f" address: 0x{address_string}"
            )
            self.adapter.connect(peer_addr, tag=1)

    def on_gap_evt_phy_update(self, ble_driver, conn_handle, status, tx_phy, rx_phy):
        phy_update = {"status": status, "tx_phy": tx_phy, "rx_phy": rx_phy}
        self.phy_q.put(phy_update)


class Peripheral(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, tester, adapter):
        self.tester = tester
        self.adapter = adapter
        logger.info(f"Peripheral adapter is {self.adapter.driver.rpc_adapter.internal}")
        self.conn_q = Queue()
        self.phy_req_q = Queue()
        self.phy_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.phy_req = None

    def start(self, adv_name):
        adv_data = BLEAdvData(complete_local_name=adv_name)
        self.adapter.driver.ble_gap_adv_data_set(adv_data)
        self.adapter.driver.ble_gap_adv_start()

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)

    def on_gap_evt_phy_update_request(
        self, ble_driver, conn_handle, peer_preferred_phys
    ):
        self.phy_req_q.put(peer_preferred_phys)

    def on_gap_evt_phy_update(self, ble_driver, conn_handle, status, tx_phy, rx_phy):
        self.phy_q.put({"status": status, "tx_phy": tx_phy, "rx_phy": rx_phy})


class PHYUPDATE(unittest.TestCase):
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

        self.central = Central(self, central)

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
        self.peripheral = Peripheral(self, peripheral)

    def test_phy_update_1mbps(self):
        # When requested PHYs are identical to current PHYs, no request is sent out
        req_phys = [driver.BLE_GAP_PHY_1MBPS, driver.BLE_GAP_PHY_1MBPS]

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, req_phys)

        phy_update_central = self.central.phy_q.get(timeout=2)
        self.assertEqual(
            req_phys, [phy_update_central["tx_phy"], phy_update_central["rx_phy"]]
        )

        self.central.stop()

    def test_phy_update_2mbps(self):
        req_phys = [driver.BLE_GAP_PHY_2MBPS, driver.BLE_GAP_PHY_2MBPS]

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, req_phys)

        phy_req_periph = self.peripheral.phy_req_q.get(timeout=2)
        logger.info(f"phy_req_periph={phy_req_periph}")
        self.assertEqual(req_phys, [phy_req_periph.tx_phys, phy_req_periph.tx_phys])

        phy_update_central = self.central.phy_q.get(timeout=2)
        logger.info(f"phy_update_central={phy_update_central}")
        self.assertEqual(
            req_phys, [phy_update_central["tx_phy"], phy_update_central["rx_phy"]]
        )
        self.assertEqual(phy_update_central["status"], BLEHci.success)

        phy_update_periph = self.peripheral.phy_q.get(timeout=2)
        logger.info(f"phy_update_central={phy_update_periph}")
        self.assertEqual(
            req_phys, [phy_update_periph["tx_phy"], phy_update_periph["rx_phy"]]
        )
        self.assertEqual(phy_update_periph["status"], BLEHci.success)

        self.central.stop()

    def test_phy_update_1and2mbps(self):
        combined_1and2mbps = driver.BLE_GAP_PHY_1MBPS | driver.BLE_GAP_PHY_2MBPS
        req_phys = [combined_1and2mbps, combined_1and2mbps]

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, req_phys)

        phy_req_periph = self.peripheral.phy_req_q.get(timeout=2)
        logger.info(f"phy_req_periph={phy_req_periph}")
        self.assertEqual(req_phys, [phy_req_periph.tx_phys, phy_req_periph.tx_phys])

        phy_update_central = self.central.phy_q.get(timeout=2)
        logger.info(f"phy_update_central={phy_update_central}")
        #  Use bitwise AND to check that the resulting PHYs match with the requested range of PHYs
        self.assertTrue(
            req_phys[0] & phy_update_central["tx_phy"] == phy_update_central["tx_phy"]
        )
        self.assertTrue(
            req_phys[1] & phy_update_central["rx_phy"] == phy_update_central["rx_phy"]
        )
        self.assertEqual(phy_update_central["status"], BLEHci.success)

        phy_update_periph = self.peripheral.phy_q.get(timeout=2)
        logger.info(f"phy_update_periph={phy_update_periph}")
        #  Use bitwise AND to check that the resulting PHYs match with the requested range of PHYs
        self.assertTrue(
            req_phys[0] & phy_update_periph["tx_phy"] == phy_update_periph["tx_phy"]
        )
        self.assertTrue(
            req_phys[1] & phy_update_periph["rx_phy"] == phy_update_periph["rx_phy"]
        )
        self.assertEqual(phy_update_periph["status"], BLEHci.success)

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
        # filename="phy_2mbps.log"
    )
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(
            output=Settings.current().test_output_directory
        ),
        argv=Settings.clean_args(),
    )
