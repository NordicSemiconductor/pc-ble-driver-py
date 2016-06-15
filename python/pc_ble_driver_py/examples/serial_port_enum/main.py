# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

import sys
from ble_driver import PCBLEDriver, SerialPortDescriptor

def main():
    descs = PCBLEDriver.enum_serial_ports()
    for d in descs:
        print("Serial port found: {}".format(d))

if __name__ == "__main__":
    main()
    quit()
