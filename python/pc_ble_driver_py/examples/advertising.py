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
import traceback
from threading                          import Condition, Lock
from pc_ble_driver_py.nrf_observers     import NrfDriverObserver

def init(conn_ic_id):
    global nrf_types, nrf_event, NrfAdapter
    from pc_ble_driver_py import config
    config.set_conn_ic(conn_ic_id)
    from pc_ble_driver_py               import nrf_types
    from pc_ble_driver_py               import nrf_event
    from pc_ble_driver_py.nrf_adapter   import NrfAdapter

def main(serial_port, baud_rate):
    print("Serial port used: {}".format(serial_port))
    adapter = None
    try:
        adapter     = NrfAdapter.open_serial(serial_port=serial_port, baud_rate=baud_rate)
        observer    = TimeoutObserver()
        adv_data    = nrf_types.BLEAdvData(complete_local_name='Example')
        adv_params  = adapter.driver.adv_params_setup()
        adv_params.timeout_s = 10

        adapter.driver.observer_register(observer)
        adapter.driver.ble_gap_adv_data_set(adv_data)
        adapter.driver.ble_gap_adv_start(adv_params)
        observer.wait_for_timeout(adv_params.timeout_s)
    except:
        traceback.print_exc()
    if adapter:
        print("Closing")
        adapter.close()

class TimeoutObserver(NrfDriverObserver):
    def __init__(self):
        self.cond = Condition(Lock())

    def on_driver_event(self, nrf_driver, event):
        if isinstance(event, nrf_event.GapEvtTimeout):
            with self.cond:
                self.cond.notify_all()
        if isinstance(event, nrf_event.GapEvtConnected):
            print("Got connected")
            with self.cond:
                self.cond.notify_all()

    def wait_for_timeout(self, timeout):
        with self.cond:
            self.cond.wait(timeout)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        init(sys.argv[1])
        baud_rate = None
        if len(sys.argv) == 4:
            baud_rate = int(sys.argv[3])
        main(sys.argv[2], baud_rate)
    else:
        print("Invalid arguments. Parameters: <conn_ic_id> <serial_port>")
        print("conn_ic_id: NRF51, NRF52")
    quit()
