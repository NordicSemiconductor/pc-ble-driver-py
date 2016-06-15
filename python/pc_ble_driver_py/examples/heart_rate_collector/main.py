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
from PCBLEDriver    import BLEUUID, BLEEnableParams, BLEEvtID, BLEAdvData, BLEGapScanParams, BLEGapConnParams, BLEGattStatusCode
from BLEAdapter     import BLEAdapter, BLEAdapterObserver

TARGET_DEV_NAME = "Nordic_HRM"
CONNECTIONS     = 2


class HRCollector(BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter    = adapter
        self.conn_q     = Queue()
        self.adapter.observer_register(self)


    def enable(self):
        ble_enable_params = BLEEnableParams(vs_uuid_count      = 1,
                                            service_changed    = False,
                                            periph_conn_count  = 0,
                                            central_conn_count = CONNECTIONS,
                                            central_sec_count  = 0)
        self.adapter.ble_enable(ble_enable_params)


    def connect_and_discover(self):
        self.adapter.ble_gap_scan_start()
        new_conn = self.conn_q.get(timeout = 60)
        self.adapter.service_discovery(new_conn)
        self.adapter.enable_notification(new_conn, BLEUUID.Standard.battery_level)
        self.adapter.enable_notification(new_conn, BLEUUID.Standard.heart_rate)


    def on_gap_evt_connected(self, context, conn_handle, peer_addr, own_addr, role, conn_params):
        print('New connection: {}'.format(conn_handle))
        self.conn_q.put(conn_handle)


    def on_gap_evt_timeout(self, context, conn_handle, src):
        if src == BLEGapTimeoutSrc.scan:
            context.ble_gap_scan_start()


    def on_gap_evt_adv_report(self, context, conn_handle, peer_addr, rssi, adv_type, adv_data):
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
            context.connect(peer_addr)


    def on_notification(self, context, conn_handle, uuid, data):
        print('Connection: {}, {} = {}'.format(conn_handle, uuid, data))


def main(serial_port):
    print('Serial port used: {}'.format(serial_port))
    adapter = BLEAdapter(serial_port=serial_port)
    adapter.open()
    collector = HRCollector(adapter)
    collector.enable()
    for i in range(CONNECTIONS):
        collector.connect_and_discover()
    sleep(30)
    print('Closing')
    adapter.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print('Enter Connectivity COM Port')
    quit()
