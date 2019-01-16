import unittest
from driver_setup import *
import logging


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

        for _ in range(settings.number_of_iterations):
            adapter.driver.open()

            if settings.nrf_family == 'NRF51':
                adapter.driver.ble_enable(BLEEnableParams(vs_uuid_count=1,
                                                          service_changed=0,
                                                          periph_conn_count=0,
                                                          central_conn_count=1,
                                                          central_sec_count=0))
            elif settings.nrf_family == 'NRF52':
                adapter.driver.ble_enable()

            adapter.driver.close()

    def tearDown(self):
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    logging.basicConfig(level=Settings.current().log_level)
    unittest.main(argv=Settings.clean_args())
