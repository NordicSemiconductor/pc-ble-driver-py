# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

import sys
sys.path.append('../../')

from PCBLEDriver import BLEEvtID, PCBLEDriver, BLEAdvData, BLEGapScanParams, BLEGapConnParams



# TARGET_DEV_NAME = "HRM Example"
# MAX_PEER_COUNT = 1
# HRM_SERVICE_UUID = 0x180D
# HRM_MEAS_CHAR_UUID = 0x2A37
# CCCD_UUID = 0x2902
# CCCD_NOTIFY = 0x01
# BLE_ADDRESS_LENGTH = 6

# connection_handle = 0
# service_start_handle = 0
# service_end_handle = 0
# hrm_char_handle = 0
# hrm_cccd_handle = 0





# def on_service_discovery_response(gattc_event):
#     global service_start_handle
#     global service_end_handle

#     if gattc_event.gatt_status != ble_driver.NRF_SUCCESS:
#         print "Error. Service discovery failed. Error code 0x{0:X}".format(gattc_event.gatt_status)
#         return

#     count = gattc_event.params.prim_srvc_disc_rsp.count

#     if count == 0:
#         print "Error. Service not found"
#         return

#     print "Received service discovery response"

#     service_list = util.service_array_to_list(gattc_event.params.prim_srvc_disc_rsp.services, count)
#     service_index = 0  # We requested to discover Heart Rate service only, so selecting first result
#     service = service_list[service_index]

#     service_start_handle = service.handle_range.start_handle
#     service_end_handle = service.handle_range.end_handle

#     print "UUID: 0x{0:04X}, start handle: 0x{1:04X}, end handle: 0x{2:04X}".format(
#         service.uuid.uuid, service_start_handle, service_end_handle)

#     start_characteristic_discovery()


# def on_characteristic_discovery_response(gattc_event):
#     global hrm_char_handle

#     if gattc_event.gatt_status != ble_driver.NRF_SUCCESS:
#         print "Error. Characteristic discovery failed. Error code 0x{0:X}".format(
#             gattc_event.gatt_status)
#         return

#     count = gattc_event.params.char_disc_rsp.count

#     print "Received characteristic discovery response, characteristics count: {}".format(count)

#     char_list = util.char_array_to_list(gattc_event.params.char_disc_rsp.chars, count)

#     for i in range(0, count):
#         characteristic = char_list[i]

#         print "Handle: 0x{0:04X}, UUID: 0x{1:04X}".format(characteristic.handle_decl,
#                                                           characteristic.uuid.uuid)

#         if characteristic.uuid.uuid == HRM_MEAS_CHAR_UUID:
#             hrm_char_handle = characteristic.handle_decl

#     start_descriptor_discovery()


# def on_descriptor_discovery_response(gattc_event):
#     global hrm_cccd_handle

#     if gattc_event.gatt_status != ble_driver.NRF_SUCCESS:
#         print "Error. Descriptor discovery failed. Error code 0x{0:X}".format(
#             gattc_event.gatt_status)
#         return

#     count = gattc_event.params.desc_disc_rsp.count

#     print "Received descriptor discovery response, descriptor count: {}".format(count)

#     desc_list = util.desc_array_to_list(gattc_event.params.desc_disc_rsp.descs, count)
#     for i in range(0, count):
#         descriptor = desc_list[i]
#         print "Handle: 0x{0:04X}, UUID: 0x{1:04X}".format(descriptor.handle, descriptor.uuid.uuid)

#         if descriptor.uuid.uuid == CCCD_UUID:
#             hrm_cccd_handle = descriptor.handle

#     print "Press enter to toggle notifications"




# def start_service_discovery():
#     print "Discovering primary services"
#     start_handle = 0x0001

#     srvc_uuid = ble_driver.ble_uuid_t()
#     srvc_uuid.type = ble_driver.BLE_UUID_TYPE_BLE
#     srvc_uuid.uuid = HRM_SERVICE_UUID

#     error_code = ble_driver.sd_ble_gattc_primary_services_discover(connection_handle, start_handle,
#                                                                    srvc_uuid)

#     if error_code != ble_driver.NRF_SUCCESS:
#         print "Failed to discover primary services"
#         return error_code

#     return ble_driver.NRF_SUCCESS


# def start_characteristic_discovery():
#     print "Discovering characteristics"

#     handle_range = ble_driver.ble_gattc_handle_range_t()
#     handle_range.start_handle = service_start_handle
#     handle_range.end_handle = service_end_handle

#     error_code = ble_driver.sd_ble_gattc_characteristics_discover(connection_handle, handle_range)

#     return error_code


# def start_descriptor_discovery():
#     print "Discovering descriptors"

#     handle_range = ble_driver.ble_gattc_handle_range_t()

#     if hrm_char_handle == 0:
#         print "Error. No HRM characteristic handle has been found"
#         return

#     handle_range.start_handle = hrm_char_handle
#     handle_range.end_handle = service_end_handle

#     ble_driver.sd_ble_gattc_descriptors_discover(connection_handle, handle_range)


# def set_hrm_cccd(value):
#     print "Setting HRM CCCD"

#     if hrm_cccd_handle == 0:
#         print "Error. No CCCD handle has been found"

#     cccd_list = [value, 0]
#     cccd_array = util.list_to_uint8_array(cccd_list)

#     write_params = ble_driver.ble_gattc_write_params_t()
#     write_params.handle = hrm_cccd_handle
#     write_params.len = len(cccd_list)
#     write_params.p_value = cccd_array.cast()
#     write_params.write_op = ble_driver.BLE_GATT_OP_WRITE_REQ
#     write_params.offset = 0

#     ble_driver.sd_ble_gattc_write(connection_handle, write_params)



TARGET_DEV_NAME = "Nordic_HRM"

class HRCollector(PCBLEDriver):
    def __init__(self, serial_port, baud_rate=115200):
        super(HRCollector, self).__init__(serial_port, baud_rate)
        self.conn_in_progress   = False
        self.conn_handlers      = list()
        self.services           = list()
        self.serv_disc_q        = Queue.Queue()
        self.char_disc_q        = Queue.Queue()
        self.desc_disc_q        = Queue.Queue()


    def scan_params_setup(self):
        return BLEGapScanParams(interval_ms = 200,
                                window_ms   = 150,
                                timeout_s   = 0x1000)


    def conn_params_setup(self):
        return BLEGapConnParams(min_conn_interval_ms = 30,
                                max_conn_interval_ms = 60,
                                conn_sup_timeout_ms  = 4000,
                                slave_latency        = 0)

    def on_gap_evt_connected(conn_handle, peer_addr, own_addr, role, conn_params):
        self.conn_handlers.append(conn_handle)
        self.conn_in_progress = False
    

    def start_service_discovery(self, conn_handle):
        self.ble_gattc_prim_srvc_disc(conn_handle, None, 0x0001)

        while True:
            self.services.extend(self.serv_disc_q.get(timeout=5))
            if self.services[-1].end_handle == 0xFFFF:
                break
            else:
                self.ble_gattc_prim_srvc_disc(conn_handle, None, self.services[-1].end_handle + 1)

        for s in self.services:
            self.ble_gattc_char_disc(conn_handle, s.start_handle, s.end_handle)
            while True:
                chars = self.char_disc_q.get(timeout=5)



    def on_gap_evt_disconnected(conn_handle, reason):
        print "Disconnected, reason: 0x{0:02X}".format(reason)
        self.conn_handlers.remove(conn_handle)


    def on_gap_evt_timeout(conn_handle, src):
        if src == BLEGapTimeoutSrc.conn:
            self.conn_in_progress = False
        elif src == BLEGapTimeoutSrc.scan:
            start_scan()


    def on_gap_evt_adv_report(conn_handle, peer_addr, rssi, adv_type, adv_data):
        dev_name_list = None
        if BLEAdvData.complete_local_name in adv_data.records:
            dev_name_list = str(adv_data.records[BLEAdvData.complete_local_name])

        elif BLEAdvData.short_local_name in adv_data.records:
            dev_name_list = str(adv_data.records[BLEAdvData.short_local_name])

        else:
            return

        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        print "Received advertisment report, address: 0x{}, device_name: {}".format(address_string,
                                                                                    dev_name)

        if (dev_name != TARGET_DEV_NAME) \
        or (len(self.conn_handlers) >= MAX_PEER_COUNT)\
        or (self.conn_in_progress):
            return

        self.ble_gap_connect(peer_addr)
        self.conn_in_progress = True


    def on_gattc_evt_prim_srvc_disc_rsp(self, conn_handle, status, services):
        if status == BLEGattStatusCode.attribute_not_found:
            self.serv_disc_q.put(None)
            return

        if status != BLEGattStatusCode.success:
            print "Error. Primary services discovery failed. Error code 0x{0:X}".format(status)
            return
        self.serv_disc_q.put(services)


    def on_gattc_evt_char_disc_rsp(self, conn_handle, status, characteristics):
        if status == BLEGattStatusCode.attribute_not_found:
            self.char_disc_q.put(None)
            return

        elif status != BLEGattStatusCode.success:
            print "Error. Characteristic discovery failed. Error code 0x{0:X}".format(status)
            return
        self.char_disc_q.put(characteristics)


    def on_gattc_evt_desc_disc_rsp(self, conn_handle, status, descriptions):
        if status == BLEGattStatusCode.attribute_not_found:
            self.char_disc_q.put(None)
            return

        if status != BLEGattStatusCode.success:
            print "Error. Description discovery failed. Error code 0x{0:X}".format(status)
            return
        self.char_disc_q.put(descriptions)


    def on_gattc_evt_hvx(conn_handle, status, error_handle, attr_handle, hvx_type, data):
        if status != BLEGattStatusCode.success:
            print "Error. Handle value notification failed. Error code 0x{0:X}".format(status)
            return

        data_string = "".join("{0:02X}".format(e) for e in data)
        print "Received handle value notification, handle: 0x{0:04X}, value: 0x{1}".format(attr_handle, data_string)


    def on_gattc_evt_write_rsp(conn_handle, status, error_handle, attr_handle, write_op, offset, data):
        if status != BLEGattStatusCode.success:
            print "Error. Write operation failed. Error code 0x{0:X}".format(status)
            return
        print "Received write response"


def main(serial_port):
    print "Serial port used: {}".format(serial_port)
    collector = HRCollector(serial_port=serial_port)
    collector.open()
    collector.ble_enable()
    collector.ble_gap_scan_start()
    collector.wait_for_event(evt = BLEEvtID.gap_evt_connected, timeout = 60)

    # cccd_value = 0

    # while True:
    #     sys.stdin.readline()
    #     cccd_value ^= CCCD_NOTIFY
    #     set_hrm_cccd(cccd_value)

    print "Closing"
    collector.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print("No connectivity serial port.")
    quit()
