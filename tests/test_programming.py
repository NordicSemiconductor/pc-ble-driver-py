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


import unittest
from queue import Queue
from functools import reduce
import time
import random
import string
import logging

from driver_setup import Settings

from pc_ble_driver_py.ble_driver import (
    BLEDriver,
    BLEEnableParams,
    BLEConfig,
    BLEConfigConnGatt,
    BLEAdvData,
    Flasher,
)

logger = logging.getLogger(__name__)


class ProgramAdapter(unittest.TestCase):
    def setUp(self):
        pass

    def test_programming(self):
        settings = Settings.current()

        serial_ports = [port for port in BLEDriver.enum_serial_ports()]

        # Check that from enumeration matches
        # kits provided from settings
        found_ports = map(lambda port: port.port, serial_ports)

        for serial_port in settings.serial_ports:
            self.assertIn(serial_port, found_ports)

        for serial_port in serial_ports:
            if serial_port.port in settings.serial_ports:
                serial_number = serial_port.serial_number
                logger.info("%s/%s deleting existing firmware", serial_port.port, serial_number)

                flasher = Flasher(serial_port=serial_port.port)
                flasher.erase()

                self.assertFalse(
                    flasher.fw_check(),
                    "#{} must be programmed because it is erased".format(
                        serial_number
                    ),
                )

                flasher.fw_flash()
                logger.info("%s/%s programmed", serial_port.port, serial_number)

                self.assertTrue(
                    flasher.fw_check(),
                    "#{} is programmed, shall not be programmed again".format(
                        serial_number
                    ),
                )

                flasher.reset()

                logger.info("%s/%s programmed successfully", serial_port.port, serial_number)

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
