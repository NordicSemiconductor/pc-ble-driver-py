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
import time
import logging
from pc_ble_driver_py.observers import BLEAdapterObserver, BLEDriverObserver

TARGET_DEV_NAME = "Nordic_HRM"
CONNECTIONS = 1
CFG_TAG = 1

# Heart Rate service UUID.
BLE_UUID_HEART_RATE_SERVICE = 0x180D
# Heart Rate Measurement characteristic UUID.
BLE_UUID_HEART_RATE_MEASUREMENT_CHAR = 0x2A37
# Battery level characteristic UUID.
BLE_UUID_BATTERY_level_CHAR = 0x2A19


HEART_RATE_BASE = 65
HEART_RATE_INCREASE = 3
HEART_RATE_LIMIT = 190

BATTERY_LEVEL_BASE = 81
BATTERY_LEVEL_INCREMENT = 1
BATTERY_LEVEL_LIMIT = 100

BLE_CONN_HANDLE_INVALID = -1


def init(conn_ic_id):
    # noinspection PyGlobalUndefined
    global config, BLEDriver, BLEAdvData, BLEEnableParams, BLEUUID, BLEConfig
    global BLEConfigConnGatt, BLEGapAdvParams, BLEGattsCharHandles, BLEGattHandle
    global BLEGattCharProps, BLEGattsCharMD, BLEGattsAttrMD, BLEGattsAttr
    global BLEGattsHVXParams, BLEGattHVXType, BLEGapConnSecMode
    global BLEAdapter
    global BLE_GATTS_SRVC_TYPE_PRIMARY, BLE_GATT_HVX_NOTIFICATION

    from pc_ble_driver_py import config

    config.__conn_ic_id__ = conn_ic_id
    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_driver import (
        BLEDriver,
        BLEAdvData,
        BLEEnableParams,
        BLEUUID,
        BLEConfig,
        BLEConfigConnGatt,
        BLEGapAdvParams,
        BLEGattsCharHandles,
        BLEGattHandle,
        BLEGattCharProps,
        BLEGattsCharMD,
        BLEGattsAttrMD,
        BLEGattsAttr,
        BLEGattsHVXParams,
        BLEGattHVXType,
        BLEGapConnSecMode,
    )

    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_adapter import BLEAdapter
    from pc_ble_driver_py.ble_driver import driver

    BLE_GATTS_SRVC_TYPE_PRIMARY = driver.BLE_GATTS_SRVC_TYPE_PRIMARY
    BLE_GATT_HVX_NOTIFICATION = driver.BLE_GATT_HVX_NOTIFICATION

    global nrf_sd_ble_api_ver
    nrf_sd_ble_api_ver = config.sd_api_ver_get()


class HRMonitor(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        super(HRMonitor, self).__init__()
        self.adapter = adapter
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.adapter.default_mtu = 250

        self.heart_rate = HEART_RATE_BASE
        self.battery_level = BATTERY_LEVEL_LIMIT
        self.connection_handle = BLE_CONN_HANDLE_INVALID
        self.advertisement_timed_out = False
        self.send_hr_notifications = False
        self.send_bl_notifications = False

    def open(self):
        self.adapter.driver.open()
        if config.__conn_ic_id__.upper() == "NRF51":
            self.adapter.driver.ble_enable(
                BLEEnableParams(
                    vs_uuid_count=1,
                    service_changed=0,
                    periph_conn_count=0,
                    central_conn_count=1,
                    central_sec_count=0,
                )
            )
        elif config.__conn_ic_id__.upper() == "NRF52":
            gatt_cfg = BLEConfigConnGatt()
            gatt_cfg.att_mtu = self.adapter.default_mtu
            gatt_cfg.tag = CFG_TAG
            self.adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)

            self.adapter.driver.ble_enable()
            self.advertisement_data_set()
            self.services_init()
            self.advertising_start()
            self.start_heart_rate_thread()

    def close(self):
        self.adapter.driver.close()

    def advertisement_data_set(self):
        import struct

        # Set the device name.
        # Set the device's available services.
        adv_data = BLEAdvData(
            complete_local_name=TARGET_DEV_NAME,
            service_16bit_uuid_complete=list(
                struct.pack("<H", BLE_UUID_HEART_RATE_SERVICE)
            ),
        )
        self.adapter.driver.ble_gap_adv_data_set(adv_data=adv_data)

    def characteristic_init(self, char_uuid, serv_handle, max_len, initial_value=[]):
        char_handles = BLEGattsCharHandles()

        props = BLEGattCharProps(notify=True)

        # read_perm = BLEGapConnSecMode()
        # read_perm.set_open()
        # write_perm = BLEGapConnSecMode()
        # write_perm.set_open()
        # cccd_md = BLEGattsAttrMD(read_perm=read_perm, write_perm=write_perm)
        # char_md = BLEGattsCharMD(char_props=props, cccd_md=cccd_md)

        char_md = BLEGattsCharMD(char_props=props)

        attr_md = BLEGattsAttrMD()
        attr = BLEGattsAttr(
            uuid=char_uuid,
            attr_md=attr_md,
            max_len=max_len,
            value=initial_value,
        )
        self.adapter.driver.ble_gatts_characteristic_add(
            serv_handle.handle, char_md, attr, char_handles
        )
        return char_handles

    def services_init(self):
        ATTR_MAX_LEN = 8  # Heart Rate Measurement Packet maximum size

        serv_handle = BLEGattHandle()
        serv_uuid = BLEUUID(BLE_UUID_HEART_RATE_SERVICE)

        self.adapter.driver.ble_gatts_service_add(
            BLE_GATTS_SRVC_TYPE_PRIMARY, serv_uuid, serv_handle
        )

        self.hr_char_handles = self.characteristic_init(
            char_uuid=BLEUUID(BLE_UUID_HEART_RATE_MEASUREMENT_CHAR),
            serv_handle=serv_handle,
            max_len=ATTR_MAX_LEN,
            initial_value=self.get_heart_rate_measurement(),
        )

        self.bl_char_handles = self.characteristic_init(
            char_uuid=BLEUUID(BLE_UUID_BATTERY_level_CHAR),
            serv_handle=serv_handle,
            max_len=ATTR_MAX_LEN,
            initial_value=[self.battery_level],
        )

        print(
            f"hr: cccd {self.hr_char_handles.cccd_handle}, value {self.hr_char_handles.value_handle}"
        )
        print(
            f"bl: cccd {self.bl_char_handles.cccd_handle}, value {self.bl_char_handles.value_handle}"
        )

    def advertising_start(self):
        adv_params = BLEGapAdvParams(interval_ms=40, timeout_s=180)
        self.adapter.driver.ble_gap_adv_start(adv_params, tag=CFG_TAG)

    def get_heart_rate_measurement(self):
        flags = 0
        self.heart_rate
        return flags, self.heart_rate

    def battery_level_generate(self):
        self.battery_level -= BATTERY_LEVEL_INCREMENT
        if self.battery_level < BATTERY_LEVEL_BASE:
            self.battery_level = BATTERY_LEVEL_LIMIT

    def heart_rate_generate(self):
        self.heart_rate += HEART_RATE_INCREASE
        if self.heart_rate > HEART_RATE_LIMIT:
            self.heart_rate = HEART_RATE_BASE

    def heart_rate_measurement_send(self):
        from pc_ble_driver_py.exceptions import NordicSemiException
        from pc_ble_driver_py.ble_driver import NRF_ERRORS

        self.heart_rate_generate()
        print(f"Sending heart rate of {self.heart_rate}")

        hvx_params = BLEGattsHVXParams(
            handle=self.hr_char_handles,
            hvx_type=BLE_GATT_HVX_NOTIFICATION,
            data=self.get_heart_rate_measurement(),
        )
        try:
            self.adapter.driver.ble_gatts_hvx(self.connection_handle, hvx_params)
            return True
        except NordicSemiException as e:
            logging.error(
                f"Failed in heart_rate_measurement_send {NRF_ERRORS.get(e.error_code, e.error_code)}"
            )
            return False

    def battery_level_send(self):
        from pc_ble_driver_py.exceptions import NordicSemiException
        from pc_ble_driver_py.ble_driver import NRF_ERRORS

        self.battery_level_generate()
        print(f"Sending battery level of {self.battery_level}")

        hvx_params = BLEGattsHVXParams(
            handle=self.bl_char_handles,
            hvx_type=BLE_GATT_HVX_NOTIFICATION,
            data=[self.battery_level],
        )
        try:
            self.adapter.driver.ble_gatts_hvx(self.connection_handle, hvx_params)
            return True
        except NordicSemiException as e:
            logging.error(
                f"Failed in battery_level_send {NRF_ERRORS.get(e.error_code, e.error_code)}"
            )
            return False

    def heart_rate_thread_func(self):
        while not self.advertisement_timed_out:
            if (
                not self.connection_handle == BLE_CONN_HANDLE_INVALID
            ) and self.send_hr_notifications:
                if not self.heart_rate_measurement_send():
                    self.send_hr_notifications = False
            if (
                not self.connection_handle == BLE_CONN_HANDLE_INVALID
            ) and self.send_bl_notifications:
                if not self.battery_level_send():
                    self.send_bl_notifications = False
            time.sleep(1)
        print("Exiting heart_rate_thread_func")

    def start_heart_rate_thread(self):
        import threading

        self.heart_rate_thread = threading.Thread(
            target=self.heart_rate_thread_func, daemon=True
        )
        self.heart_rate_thread.start()

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        print(f"Connected, connection handle 0x{conn_handle:04X}")
        self.connection_handle = conn_handle

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        print(f"Disconnected, connection_handle 0x{conn_handle:04X}, reason {reason}")
        self.connection_handle = BLE_CONN_HANDLE_INVALID
        self.send_hr_notifications = False
        self.send_bl_notifications = False
        self.advertising_start()

    def on_gatts_evt_write(
        self,
        ble_driver,
        conn_handle,
        attr_handle,
        uuid,
        op,
        auth_required,
        offset,
        length,
        data,
    ):
        if attr_handle == self.hr_char_handles.cccd_handle:
            import pc_ble_driver_py.ble_driver_types as util

            write_data = util.uint8_array_to_list(data, length)
            self.send_hr_notifications = (
                write_data[0] == BLEGattHVXType.notification.value
            )
        if attr_handle == self.bl_char_handles.cccd_handle:
            import pc_ble_driver_py.ble_driver_types as util

            write_data = util.uint8_array_to_list(data, length)
            self.send_bl_notifications = (
                write_data[0] == BLEGattHVXType.notification.value
            )

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        print("Advertisement timed out")
        self.advertisement_timed_out = True


def main(selected_serial_port):
    print("Serial port used: {}".format(selected_serial_port))
    driver = BLEDriver(
        serial_port=selected_serial_port,
        auto_flash=False,
        baud_rate=1000000,
        log_severity_level="info",
    )

    adapter = BLEAdapter(driver)
    collector = HRMonitor(adapter)
    collector.open()

    while not collector.advertisement_timed_out:
        time.sleep(1)

    collector.close()


def item_choose(item_list):
    for i, it in enumerate(item_list):
        print("\t{} : {}".format(i, it))
    print(" ")

    while True:
        try:
            choice = int(input("Enter your choice: "))
            if (choice >= 0) and (choice < len(item_list)):
                break
        except Exception:
            pass
        print("\tTry again...")
    return choice


if __name__ == "__main__":
    logging.basicConfig(
        level="DEBUG",
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    serial_port = None
    if len(sys.argv) < 2:
        print("Please specify connectivity IC identifier (NRF51, NRF52)")
        exit(1)
    init(sys.argv[1])
    if len(sys.argv) == 3:
        serial_port = sys.argv[2]
    else:
        descs = BLEDriver.enum_serial_ports()
        choices = ["{}: {}".format(d.port, d.serial_number) for d in descs]
        choice = item_choose(choices)
        serial_port = descs[choice].port
    main(serial_port)
    quit()
