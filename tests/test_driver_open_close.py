import unittest
from driver_setup import *
import logging
import time

logger = logging.getLogger(__name__)

from pc_ble_driver_py.ble_driver import BLEDriver, \
    BLEEnableParams, BLEConfig, BLEConfigConnGatt

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
            log_severity_level=settings.driver_log_level
        )
        adapter = BLEAdapter(driver)

        logger.info('Number of iterations: %s', settings.number_of_iterations)

        for _ in range(0, settings.number_of_iterations):
            adapter.open()

            if settings.nrf_family == 'NRF51':
                adapter.driver.ble_enable(BLEEnableParams(vs_uuid_count=1,
                                                          service_changed=0,
                                                          periph_conn_count=0,
                                                          central_conn_count=1,
                                                          central_sec_count=0))
            elif settings.nrf_family == 'NRF52':
                gatt_cfg = BLEConfigConnGatt()
                gatt_cfg.att_mtu = adapter.default_mtu
                gatt_cfg.tag = 1
                adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
                adapter.driver.ble_enable()

            adapter.driver.ble_gap_scan_start()
            time.sleep(1)
            adapter.close()


    def tearDown(self):
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    logging.basicConfig(level=Settings.current().log_level, format='%(asctime)s [%(thread)d/%(threadName)s] %(message)s')
    unittest.main(argv=Settings.clean_args())
