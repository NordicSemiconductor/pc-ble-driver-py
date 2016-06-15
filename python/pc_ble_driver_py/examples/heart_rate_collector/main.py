# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

import logging
logging.basicConfig()
from Queue  import Queue, Empty
from time   import sleep

import sys
sys.path.append('../../')
from PCBLEDriver    import BLEUUID, BLEEvtID, BLEAdvData, BLEGapScanParams, BLEGapConnParams, BLEGattStatusCode
from BLEAdapter     import BLEAdapter

TARGET_DEV_NAME = "Nordic_HRM"


class HRCollector(BLEAdapter):
    def __init__(self, serial_port, baud_rate=115200):
        super(HRCollector, self).__init__(serial_port, baud_rate)
        self.conn_q = Queue()


    def scan_params_setup(self):
        return BLEGapScanParams(interval_ms = 200,
                                window_ms   = 150,
                                timeout_s   = 0x1000)


    def conn_params_setup(self):
        return BLEGapConnParams(min_conn_interval_ms = 30,
                                max_conn_interval_ms = 60,
                                conn_sup_timeout_ms  = 4000,
                                slave_latency        = 0)


    def on_gap_evt_connected(self, conn_handle, peer_addr, own_addr, role, conn_params):
        super(HRCollector, self).on_gap_evt_connected(conn_handle, peer_addr, own_addr, role, conn_params)
        print('New connection: {}'.format(conn_handle))
        self.conn_q.put(conn_handle)
        # self.ble_gap_scan_start()


    def on_gap_evt_timeout(self, conn_handle, src):
        super(HRCollector, self).on_gap_evt_timeout(conn_handle, src)
        if src == BLEGapTimeoutSrc.scan:
            self.ble_gap_scan_start()


    def on_gap_evt_adv_report(self, conn_handle, peer_addr, rssi, adv_type, adv_data):
        super(HRCollector, self).on_gap_evt_adv_report(conn_handle, peer_addr, rssi, adv_type, adv_data)

        dev_name_list = None
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]

        else:
            return

        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        print('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                    dev_name))

        if (dev_name == TARGET_DEV_NAME):
            self.connect(peer_addr)

    def on_notification(self, conn_handle, uuid, data):
        print('Connection: {}, {} = {}'.format(conn_handle, uuid, data))


def main(serial_port):
    print "Serial port used: {}".format(serial_port)
    collector = HRCollector(serial_port=serial_port)
    collector.open()
    collector.ble_enable()
    collector.ble_gap_scan_start()
    try:
        while(True):
            new_conn = collector.conn_q.get(timeout = 60)
            collector.service_discovery(new_conn)
            collector.enable_notification(new_conn, BLEUUID.Standard.battery_level)
            collector.enable_notification(new_conn, BLEUUID.Standard.heart_rate)

    except(Empty):
        print('Closing')
        collector.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print('Enter Connectivity COM Port')
    quit()
