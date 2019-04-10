import unittest
from driver_setup import *
import logging
import time

logger = logging.getLogger(__name__)

from pc_ble_driver_py.observers import BLEDriverObserver, BLEAdapterObserver
from pc_ble_driver_py.ble_driver import (
    BLEDriver,
    BLEEnableParams,
    BLEConfig,
    BLEConfigConnGatt,
    BLEAdvData,
)


class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.adv_received = False

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
        address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        logger.info(
            "Received advertisment report, address: 0x%s, device_name: %s",
            address_string,
            dev_name,
        )

        self.adv_received = True


class DriverOpenClose(unittest.TestCase):
    def setUp(self):
        pass

    def test_open_close(self):
        settings = Settings.current()
        driver = BLEDriver(
            serial_port=settings.serial_ports[0],
            auto_flash=False,
            baud_rate=settings.baud_rate,
            retransmission_interval=settings.retransmission_interval,
            response_timeout=settings.response_timeout,
            log_severity_level=settings.driver_log_level,
        )
        adapter = BLEAdapter(driver)
        central = Central(adapter)

        logger.info("Number of iterations: %s", settings.number_of_iterations)

        for _ in range(0, settings.number_of_iterations):
            adapter.open()

            if settings.nrf_family == "NRF51":
                adapter.driver.ble_enable(
                    BLEEnableParams(
                        vs_uuid_count=1,
                        service_changed=0,
                        periph_conn_count=0,
                        central_conn_count=1,
                        central_sec_count=0,
                    )
                )
            elif settings.nrf_family == "NRF52":
                gatt_cfg = BLEConfigConnGatt()
                gatt_cfg.att_mtu = adapter.default_mtu
                gatt_cfg.tag = 1
                adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
                adapter.driver.ble_enable()

            adapter.driver.ble_gap_scan_start()
            time.sleep(1)
            self.assertTrue(central.adv_received)
            adapter.close()

    def tearDown(self):
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        level=Settings.current().log_level,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    unittest.main(argv=Settings.clean_args())
