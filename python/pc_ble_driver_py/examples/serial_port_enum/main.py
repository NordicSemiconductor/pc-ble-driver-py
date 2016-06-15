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
    print("enum_serial_ports: {} serial ports found".format(len(descs)))
    for i, d in enumerate(descs):
        print("Serial port #{}:".format(i))
        print("|")
        print("|-    Port: \"{}\"".format(d.port))
        print("|-    Manufacturer: \"{}\"".format(d.manufacturer))
        print("|-    Serial Number: \"{}\"".format(d.serial_number))
        print("|-    PnP ID: \"{}\"".format(d.pnp_id))
        print("|-    Location ID: \"{}\"".format(d.location_id))
        print("|-    Vendor ID: \"{}\"".format(d.vendor_id))
        print("|_    Product ID: \"{}\"".format(d.product_id))

if __name__ == "__main__":
    main()
    quit()
