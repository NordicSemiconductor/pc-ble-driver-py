# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

"""
Example on use of s130_nrf51_ble_driver python binding library.

The example shows how to initialize library and configure the nRF51 to start advertising.
"""

# Add location of binding library to path
import sys
sys.path.append("../..")
sys.path.append("../../lib")
sys.path.append("../../..")
sys.path.append("../../../Debug")

import platform
import ctypes

SERIAL_PORT = ""

if platform.system() == "Windows":
    # Load the DLL into memory (instead of copying to current directory)
    ctypes.cdll.LoadLibrary('../../../pc-ble-driver/Debug/pc_ble_driver_shared.dll') 
# Import the binding library
import pc_ble_driver    as ble_driver
import ble_driver_util  as util

import traceback
from time import sleep

connection_handle = None
advertisement_timed_out = False


def log_message_handler(m_adapter, severity, log_message):
    unused = severity
    try:
        print "Log: {}".format(log_message)
    except Exception, ex:
        print "Exception: {}".format(str(ex))


def ble_evt_handler(m_adapter, ble_event):
    global connection_handle
    global advertisement_timed_out
    try:
        if ble_event is None:
            print "Received empty ble_event"
            return

        evt_id = ble_event.header.evt_id

        if evt_id == ble_driver.BLE_GAP_EVT_CONNECTED:
            connection_handle = ble_event.evt.gap_evt.conn_handle
            print "Connected, connection handle 0x{:04X}".format(connection_handle)

        elif evt_id == ble_driver.BLE_GAP_EVT_DISCONNECTED:
            print "Disconnected"
            start_advertising()

        elif evt_id == ble_driver.BLE_GAP_EVT_TIMEOUT:
            print "Advertisement timed out"
            advertisement_timed_out = True

        elif evt_id == ble_driver.BLE_GAP_EVT_SEC_PARAMS_REQUEST:
            print "Received Security Parameters request"
            ble_driver.sd_ble_gap_sec_params_reply(connection_handle,
                                                   ble_driver.BLE_GAP_SEC_STATUS_SUCCESS,
                                                   None, None)

        elif evt_id == ble_driver.BLE_GATTS_EVT_SYS_ATTR_MISSING:
            print "Received System Attribute Missing event"
            ble_driver.sd_ble_gatts_sys_attr_set(connection_handle, None, 0, 0)

        elif evt_id == ble_driver.BLE_GATTS_EVT_WRITE:
            write_evt = ble_event.evt.gatts_evt.params.write
            handle = write_evt.handle
            operation = write_evt.op
            offset = write_evt.offset
            length = write_evt.len
            data = write_evt.data

            data_list = util.uint8_array_to_list(data, length)

            print "Received Write event: Handle:{}, op:{}, offset:{}, len:{}, data:{}".format(
                handle, operation, offset, len, data_list)

        else:
            print "Received event with ID: 0x{0:02X}".format(evt_id)

    except Exception, ex:
        print "Exception: {}".format(str(ex))
        print traceback.extract_tb(sys.exc_info()[2])


def init_ble_stack(m_adapter):
    ble_enable_params = ble_driver.ble_enable_params_t()
    ble_enable_params.gatts_enable_params.attr_tab_size = ble_driver.BLE_GATTS_ATTR_TAB_SIZE_DEFAULT
    ble_enable_params.gatts_enable_params.service_changed = False
    ble_enable_params.gap_enable_params.periph_conn_count = 1;
    ble_enable_params.gap_enable_params.central_conn_count = 7;
    ble_enable_params.gap_enable_params.central_sec_count = 1;
    ble_enable_params.common_enable_params.p_conn_bw_counts = None;
    ble_enable_params.common_enable_params.vs_uuid_count = 10;

    error_code = ble_driver.sd_ble_enable(m_adapter, ble_enable_params, None)
    print ""
    print error_code
    print ble_driver.NRF_SUCCESS
    print ""
    if error_code == ble_driver.NRF_SUCCESS:
        return error_code

    if error_code == ble_driver.NRF_ERROR_INVALID_STATE:
        print "BLE stack already enabled"
        return ble_driver.NRF_SUCCESS

    print "Failed to enable BLE stack"
    print str(error_code)
    print "Oko"
    return error_code


def set_adv_data(m_adapter):
    device_name = "Example"
    device_name_utf8 = [ord(character) for character in list(device_name)]

    data_type = [ble_driver.BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME]

    payload = list(data_type + device_name_utf8)
    payload_length = len(payload)

    data_list = [payload_length] + payload
    data_length = len(data_list)

    data_array = util.list_to_uint8_array(data_list)
    # To get the correct pointer type, call cast() on the array object.
    data_array_pointer = data_array.cast()

    error_code = ble_driver.sd_ble_gap_adv_data_set(m_adapter, data_array_pointer, data_length, None, 0)

    if error_code != ble_driver.NRF_SUCCESS:
        print "Failed to set advertisement data. Error code: 0x{0:02X}".format(error_code)
        return

    print "Advertising data set"


def start_advertising(m_adapter):
    adv_params = ble_driver.ble_gap_adv_params_t()

    adv_params.type = ble_driver.BLE_GAP_ADV_TYPE_ADV_IND
    adv_params.p_peer_addr = None  # Undirected advertisement.
    adv_params.fp = ble_driver.BLE_GAP_ADV_FP_ANY
    adv_params.p_whitelist = None
    adv_params.interval = util.msec_to_units(40, util.UNIT_0_625_MS)
    adv_params.timeout = 180  # Advertising timeout 180 seconds

    error_code = ble_driver.sd_ble_gap_adv_start(m_adapter, adv_params)

    if error_code != ble_driver.NRF_SUCCESS:
        print "Failed to start advertising. Error code: 0x{0:02X}".format(error_code)
        return

    print "Started advertising"

def status_handler(adapter, status_code, status_message):
    pass

def main(serial_port):
    print "Serial port used: {}".format(serial_port)
    phy = ble_driver.sd_rpc_physical_layer_create_uart('COM68',
                                                       115200,
                                                       ble_driver.SD_RPC_FLOW_CONTROL_NONE,
                                                       ble_driver.SD_RPC_PARITY_NONE);

    data_link_layer = ble_driver.sd_rpc_data_link_layer_create_bt_three_wire(phy, 100);

    transport_layer = ble_driver.sd_rpc_transport_layer_create(data_link_layer, 100);

    m_adapter = ble_driver.sd_rpc_adapter_create(transport_layer);
    adapter     = None
    error_code  = ble_driver.sd_rpc_open(m_adapter, status_handler, ble_evt_handler, log_message_handler)

    if error_code != ble_driver.NRF_SUCCESS:
        print "Failed to open the nRF51 BLE Driver"
        return

    error_code = init_ble_stack(m_adapter)

    if error_code != ble_driver.NRF_SUCCESS:
        return

    set_adv_data(m_adapter)
    start_advertising(m_adapter)

    while not advertisement_timed_out:
        sleep(1)

    ble_driver.sd_rpc_close(m_adapter)

    print "Closing"

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else SERIAL_PORT)
    quit()
