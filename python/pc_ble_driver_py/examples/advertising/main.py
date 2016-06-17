# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

import sys
from threading  import Condition, Lock
from ble_driver import BLEDriver, BLEDriverObserver, BLEAdvData, BLEEvtID


class TimeoutObserver(BLEDriverObserver):
    def __init__(self):
        self.cond = Condition(Lock())

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        with self.cond:
            self.cond.notify_all()

    def wait_for_timeout(self):
        with self.cond:
            self.cond.wait()


def main(serial_port):
    print("Serial port used: {}".format(serial_port))
    driver      = BLEDriver(serial_port=serial_port)
    observer    = TimeoutObserver()
    adv_data    = BLEAdvData(complete_local_name='Example')

    driver.observer_register(observer)
    driver.open()
    driver.ble_enable()
    driver.ble_gap_adv_data_set(adv_data)
    driver.ble_gap_adv_start()
    observer.wait_for_timeout()

    print("Closing")
    driver.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print("No connectivity serial port.")
    quit()
