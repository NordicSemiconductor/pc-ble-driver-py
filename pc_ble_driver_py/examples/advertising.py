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
from threading import Condition, Lock
from pc_ble_driver_py.observers import BLEDriverObserver


def init(conn_ic_id):
    # noinspection PyGlobalUndefined
    global BLEDriver, BLEAdvData, BLEEvtID, BLEEnableParams, config, BLEAdvData
    from pc_ble_driver_py import config

    config.__conn_ic_id__ = conn_ic_id
    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_driver import (
        BLEDriver,
        BLEAdvData,
        BLEEvtID,
        BLEEnableParams,
    )


def main(serial_port):
    print("Serial port used: {}".format(serial_port))
    driver = BLEDriver(serial_port=serial_port, baud_rate=1000000)
    observer = TimeoutObserver()
    adv_data = BLEAdvData(complete_local_name="pc_ble_driver_py")

    driver.observer_register(observer)
    driver.open()
    if config.__conn_ic_id__.upper() == "NRF51":
        driver.ble_enable(
            BLEEnableParams(
                vs_uuid_count=0,
                service_changed=0,
                periph_conn_count=1,
                central_conn_count=0,
                central_sec_count=0,
            )
        )
    elif config.__conn_ic_id__.upper() == "NRF52":
        driver.ble_enable()
    driver.ble_gap_adv_data_set(adv_data)
    driver.ble_gap_adv_start()
    observer.wait_for_timeout()

    print("Closing")
    driver.close()


class TimeoutObserver(BLEDriverObserver):
    def __init__(self, *args, **kwargs):
        super(BLEDriverObserver, self).__init__(*args, **kwargs)
        self.cond = Condition(Lock())

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        with self.cond:
            self.cond.notify_all()

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        with self.cond:
            self.cond.notify_all()

    def wait_for_timeout(self):
        with self.cond:
            self.cond.wait()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        init(sys.argv[1])
        main(sys.argv[2])
    else:
        print("Invalid arguments. Parameters: <conn_ic_id> <serial_port>")
        print("conn_ic_id: NRF51, NRF52")
    quit()
