# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.


from PCBLEDriver import PCBLEDriver, BLEAdvData


def main(serial_port):
    print "Serial port used: {}".format(serial_port)
    driver = PCBLEDriver(serial_port=serial_port)
    driver.open()
    driver.ble_enable()
    adv_data = BLEAdvData(complete_local_name='Example')
    driver.ble_gap_adv_data_set(adv_data)
    driver.ble_gap_adv_start()
    driver.wait_for_event(evt = BLEEvtID.gap_evt_timeout, timeout=200)
    print "Closing"
    driver.close()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else SERIAL_PORT)
    quit()
