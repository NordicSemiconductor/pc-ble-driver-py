import unittest
from driver_setup import *
import logging
from pprint import pformat

logger = logging.getLogger(__name__)

from pc_ble_driver_py.ble_driver import (
    BLEDriver,
    BLEEnableParams,
    BLEConfig,
    BLEConfigConnGatt,
    BLEUUIDBase,
    BLEGattStatusCode,
    driver,
)


class BLECommonAPITest(unittest.TestCase):
    def setUp(self):
        settings = Settings.current()
        self.driver = BLEDriver(
            serial_port=settings.serial_ports[0],
            auto_flash=False,
            baud_rate=settings.baud_rate,
            retransmission_interval=settings.retransmission_interval,
            response_timeout=settings.response_timeout,
            log_severity_level=settings.driver_log_level,
        )
        self.adapter = BLEAdapter(self.driver)
        self.adapter.open()

        if settings.nrf_family == "NRF51":
            self.adapter.driver.ble_enable(
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
            gatt_cfg.att_mtu = self.adapter.default_mtu
            gatt_cfg.tag = 1
            self.adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
            self.adapter.driver.ble_enable()

    def test_ble_vs_uuid_add(self):
        logger.info("Adding BLE_UUID_TYPE_VENDOR_BEGIN")

        data = [
            0x12,
            0x34,
            0x56,
            0x78,
            0xE4,
            0x2F,
            0x42,
            0x98,
            0xD6,
            0x44,
            0xB6,
            0x1B,
            0x00,
            0x00,
            0xDF,
            0xC8,
        ]

        base = BLEUUIDBase(data, driver.BLE_UUID_TYPE_VENDOR_BEGIN)
        self.driver.ble_vs_uuid_add(base)
        self.assertEqual(base.type, driver.BLE_UUID_TYPE_VENDOR_BEGIN)

    def test_ble_version_get(self):
        version = self.adapter.get_version()
        self.assertIsNotNone(version)
        self.assertIsNotNone(version.softdevice_info)
        self.assertIsNotNone(version.subversion_number)
        self.assertIsNotNone(version.version_number)

    def tearDown(self):
        self.adapter.close()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        level=Settings.current().log_level,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    unittest.main(argv=Settings.clean_args())
