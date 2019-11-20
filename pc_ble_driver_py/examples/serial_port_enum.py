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


# noinspection PyGlobalUndefined
def init(conn_ic_id):
    global BLEDriver, Flasher
    from pc_ble_driver_py import config

    config.__conn_ic_id__ = conn_ic_id
    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_driver import BLEDriver, Flasher


def main(selected_port):
    descs = BLEDriver.enum_serial_ports()
    print("enum_serial_ports: {} serial ports found".format(len(descs)))
    for i, d in enumerate(descs):
        print("\nSerial port #{}:".format(i))
        print("|")
        print('|-  Port: "{}"'.format(d.port))
        print('|-  Manufacturer: "{}"'.format(d.manufacturer))
        print('|-  Serial Number: "{}"'.format(d.serial_number))
        print('|-  PnP ID: "{}"'.format(d.pnp_id))
        print('|-  Location ID: "{}"'.format(d.location_id))
        print('|-  Vendor ID: "{}"'.format(d.vendor_id))
        print('|_  Product ID: "{}"'.format(d.product_id))
    if selected_port is not None:
        flasher = Flasher(serial_port=selected_port)
        if flasher.fw_check():
            print(
                'Port "{}" already flashed with connectivity firmware'.format(
                    selected_port
                )
            )
        else:
            print('Flashing Port "{}"'.format(selected_port))
            flasher.fw_flash()
            print("Firmware flashed")


if __name__ == "__main__":
    port = None
    if len(sys.argv) < 2:
        print("Please specify connectivity IC identifier (NRF51, NRF52)")
        exit(1)
    init(sys.argv[1])
    if len(sys.argv) == 3:
        port = sys.argv[2]
    main(port)
    quit()
