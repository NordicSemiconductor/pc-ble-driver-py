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

import pc_ble_driver_py.config as config
from pc_ble_driver_py.exceptions import NordicSemiException

nrf_sd_ble_api_ver = config.sd_api_ver_get()

if nrf_sd_ble_api_ver == 2:
    import pc_ble_driver_py.lib.nrf_ble_driver_sd_api_v2 as ble_driver
elif nrf_sd_ble_api_ver == 5:
    import pc_ble_driver_py.lib.nrf_ble_driver_sd_api_v5 as ble_driver
else:
    raise NordicSemiException(
        "SoftDevice API {} not supported".format(nrf_sd_ble_api_ver)
    )

UNIT_0_625_MS = 625  # Unit used for scanning and advertising parameters
UNIT_1_25_MS = 1250  # Unit used for connection interval parameters
UNIT_10_MS = 10000  # Unit used for supervision timeout parameter


def msec_to_units(time_ms, resolution):
    """Convert milliseconds to BLE specific time units."""
    units = time_ms * 1000 / resolution
    return int(units)


def units_to_msec(units, resolution):
    """Convert BLE specific units to milliseconds."""
    time_ms = units * float(resolution) / 1000
    return time_ms


def char_array_to_list(array_pointer, length):
    """Convert char_array to python list."""
    data_array = ble_driver.char_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def uint8_array_to_list(array_pointer, length):
    """Convert uint8_array to python list."""
    data_array = ble_driver.uint8_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def uint16_array_to_list(array_pointer, length):
    """Convert uint16_array to python list."""
    data_array = ble_driver.uint16_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def service_array_to_list(array_pointer, length):
    """Convert ble_gattc_service_array to python list."""
    data_array = ble_driver.ble_gattc_service_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def include_array_to_list(array_pointer, length):
    """Convert ble_gattc_include_array to python list."""
    data_array = ble_driver.ble_gattc_include_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def ble_gattc_char_array_to_list(array_pointer, length):
    """Convert ble_gattc_char_array to python list."""
    data_array = ble_driver.ble_gattc_char_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def desc_array_to_list(array_pointer, length):
    """Convert ble_gattc_desc_array to python list."""
    data_array = ble_driver.ble_gattc_desc_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def handle_value_array_to_list(array_pointer, length):
    """Convert ble_gattc_handle_value_array to python list."""
    data_array = ble_driver.ble_gattc_handle_value_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def attr_info_array_to_list(array_pointer, length):
    """Convert ble_gattc_attr_info_array to python list."""
    data_array = ble_driver.ble_gattc_attr_info_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def attr_info16_array_to_list(array_pointer, length):
    """Convert ble_gattc_attr_info16_array to python list."""
    data_array = ble_driver.ble_gattc_attr_info16_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def attr_info128_array_to_list(array_pointer, length):
    """Convert ble_gattc_attr_info128_array to python list."""
    data_array = ble_driver.ble_gattc_attr_info128_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def serial_port_desc_array_to_list(array_pointer, length):
    """Convert sd_rpc_serial_port_desc_array to python list."""
    data_array = ble_driver.sd_rpc_serial_port_desc_array.frompointer(array_pointer)
    data_list = _populate_list(data_array, length)
    return data_list


def _populate_list(data_array, length):
    data_list = []
    for i in range(0, length):
        data_list.append(data_array[i])
    return data_list


def list_to_char_array(data_list):
    """Convert python list to char_array."""

    data_array = _populate_array(data_list, ble_driver.char_array)
    return data_array


def list_to_uint8_array(data_list):
    """Convert python list to uint8_array."""

    data_array = _populate_array(data_list, ble_driver.uint8_array)
    return data_array


def list_to_uint16_array(data_list):
    """Convert python list to uint16_array."""

    data_array = _populate_array(data_list, ble_driver.uint16_array)
    return data_array


def list_to_service_array(data_list):
    """Convert python list to ble_gattc_service_array."""

    data_array = _populate_array(data_list, ble_driver.ble_gattc_service_array)
    return data_array


def list_to_include_array(data_list):
    """Convert python list to ble_gattc_include_array."""

    data_array = _populate_array(data_list, ble_driver.ble_gattc_include_array)
    return data_array


def list_to_ble_gattc_char_array(data_list):
    """Convert python list to ble_gattc_char_array."""

    data_array = _populate_array(data_list, ble_driver.ble_gattc_char_array)
    return data_array


def list_to_desc_array(data_list):
    """Convert python list to ble_gattc_desc_array."""

    data_array = _populate_array(data_list, ble_driver.ble_gattc_desc_array)
    return data_array


def list_to_handle_value_array(data_list):
    """Convert python list to ble_gattc_handle_value_array."""

    data_array = _populate_array(data_list, ble_driver.ble_gattc_handle_value_array)
    return data_array


def list_to_serial_port_desc_array(data_list):
    """Convert python list to sd_rpc_serial_port_desc_array."""

    data_array = _populate_array(data_list, ble_driver.sd_rpc_serial_port_desc_array)
    return data_array


def _populate_array(data_list, array_type):
    length = len(data_list)
    data_array = array_type(length)
    for i in range(0, length):
        data_array[i] = data_list[i]
    return data_array
