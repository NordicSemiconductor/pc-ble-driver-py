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
import collections
import functools
import re
import subprocess
import sys
import time
import traceback
import queue
import logging
from abc import abstractmethod
from threading import Thread, Lock

from enum import Enum
from typing import List

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec

import wrapt

from pc_ble_driver_py.observers import *

logger = logging.getLogger(__name__)

NoneType = type(None)
driver = None

import pc_ble_driver_py.config as config

nrf_sd_ble_api_ver = config.sd_api_ver_get()
# Load pc_ble_driver

ATT_MTU_DEFAULT = None

# Number of seconds to wait before getting items in queue
# Supports
WORKER_QUEUE_WAIT_TIME = 1

if nrf_sd_ble_api_ver == 2:
    import pc_ble_driver_py.lib.nrf_ble_driver_sd_api_v2 as driver

    ATT_MTU_DEFAULT = driver.GATT_MTU_SIZE_DEFAULT
elif nrf_sd_ble_api_ver == 5:
    import pc_ble_driver_py.lib.nrf_ble_driver_sd_api_v5 as driver

    ATT_MTU_DEFAULT = driver.BLE_GATT_ATT_MTU_DEFAULT
else:
    raise NordicSemiException(
        "SoftDevice API {} not supported".format(nrf_sd_ble_api_ver)
    )

import pc_ble_driver_py.ble_driver_types as util
from pc_ble_driver_py.exceptions import NordicSemiException


NRF_ERRORS = {
    getattr(driver, name): name
    for name in dir(driver) if name.startswith('NRF_ERROR_')
}


def NordicSemiErrorCheck(wrapped=None, expected=driver.NRF_SUCCESS):
    if wrapped is None:
        return functools.partial(NordicSemiErrorCheck, expected=expected)

    @wrapt.decorator
    def wrapper(wrapped, _instance, args, kwargs):
        err_code = wrapped(*args, **kwargs)
        if err_code != expected:
            raise NordicSemiException(
                "Failed to {}. Error code: {}".format(
                    wrapped.__name__, NRF_ERRORS.get(err_code, err_code)
                ),
                error_code=err_code,
            )

    return wrapper(wrapped)


class EnumWithOffsets(Enum):
    """An extesion of Enum allowing lookup of intermediary values. The
    intermediary values must directly follow a member with a name that ends with
    "_begin". Names of intermediate members will be rendred like
    "name_of_previous_member+0x4"."""
    @classmethod
    def _missing_(cls, value):
        members = cls.__members__.values()
        preceding_member = max(filter(lambda x: x.value < value, members),
                               key=lambda x: x.value, default=None)
        if preceding_member and preceding_member.name.endswith('_begin'):
            inst = super(Enum, cls).__new__(cls)
            inst._name_ = preceding_member.name + "+" + hex(value - preceding_member.value)
            inst._value_ = value
            return inst


class BLEEvtID(Enum):
    gap_evt_connected = driver.BLE_GAP_EVT_CONNECTED
    gap_evt_disconnected = driver.BLE_GAP_EVT_DISCONNECTED
    gap_evt_sec_params_request = driver.BLE_GAP_EVT_SEC_PARAMS_REQUEST
    gap_evt_sec_info_request = driver.BLE_GAP_EVT_SEC_INFO_REQUEST
    gap_evt_passkey_display = driver.BLE_GAP_EVT_PASSKEY_DISPLAY
    gap_evt_key_pressed = driver.BLE_GAP_EVT_KEY_PRESSED
    gap_evt_lesc_dhkey_request = driver.BLE_GAP_EVT_LESC_DHKEY_REQUEST
    gap_evt_scan_req_report = driver.BLE_GAP_EVT_SCAN_REQ_REPORT
    gap_evt_sec_request = driver.BLE_GAP_EVT_SEC_REQUEST
    gap_evt_adv_report = driver.BLE_GAP_EVT_ADV_REPORT
    gap_evt_timeout = driver.BLE_GAP_EVT_TIMEOUT
    gap_evt_conn_param_update_request = driver.BLE_GAP_EVT_CONN_PARAM_UPDATE_REQUEST
    gap_evt_conn_param_update = driver.BLE_GAP_EVT_CONN_PARAM_UPDATE
    gap_evt_rssi_changed = driver.BLE_GAP_EVT_RSSI_CHANGED
    gap_evt_auth_status = driver.BLE_GAP_EVT_AUTH_STATUS
    gap_evt_auth_key_request = driver.BLE_GAP_EVT_AUTH_KEY_REQUEST
    gap_evt_conn_sec_update = driver.BLE_GAP_EVT_CONN_SEC_UPDATE
    gattc_evt_write_rsp = driver.BLE_GATTC_EVT_WRITE_RSP
    gattc_evt_read_rsp = driver.BLE_GATTC_EVT_READ_RSP
    gattc_evt_hvx = driver.BLE_GATTC_EVT_HVX
    gattc_evt_prim_srvc_disc_rsp = driver.BLE_GATTC_EVT_PRIM_SRVC_DISC_RSP
    gattc_evt_char_disc_rsp = driver.BLE_GATTC_EVT_CHAR_DISC_RSP
    gattc_evt_desc_disc_rsp = driver.BLE_GATTC_EVT_DESC_DISC_RSP
    gatts_evt_hvc = driver.BLE_GATTS_EVT_HVC
    gatts_evt_write = driver.BLE_GATTS_EVT_WRITE
    gatts_evt_sys_attr_missing = driver.BLE_GATTS_EVT_SYS_ATTR_MISSING

    if nrf_sd_ble_api_ver == 2:
        evt_tx_complete = driver.BLE_EVT_TX_COMPLETE

    if nrf_sd_ble_api_ver == 5:
        gatts_evt_exchange_mtu_request = driver.BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST
        gattc_evt_exchange_mtu_rsp = driver.BLE_GATTC_EVT_EXCHANGE_MTU_RSP
        gap_evt_data_length_update = driver.BLE_GAP_EVT_DATA_LENGTH_UPDATE
        gap_evt_data_length_update_request = (
            driver.BLE_GAP_EVT_DATA_LENGTH_UPDATE_REQUEST
        )
        gattc_evt_write_cmd_tx_complete = driver.BLE_GATTC_EVT_WRITE_CMD_TX_COMPLETE
        gatts_evt_hvn_tx_complete = driver.BLE_GATTS_EVT_HVN_TX_COMPLETE
        gap_evt_phy_update_request = driver.BLE_GAP_EVT_PHY_UPDATE_REQUEST
        gap_evt_phy_update = driver.BLE_GAP_EVT_PHY_UPDATE


class BLEEnableParams(object):
    def __init__(
        self,
        vs_uuid_count,
        service_changed,
        periph_conn_count,
        central_conn_count,
        central_sec_count,
        attr_tab_size=driver.BLE_GATTS_ATTR_TAB_SIZE_DEFAULT,
        att_mtu=ATT_MTU_DEFAULT,
    ):
        self.vs_uuid_count = vs_uuid_count
        self.attr_tab_size = attr_tab_size
        self.service_changed = service_changed
        self.periph_conn_count = periph_conn_count
        self.central_conn_count = central_conn_count
        self.central_sec_count = central_sec_count
        if nrf_sd_ble_api_ver >= 3:
            self.att_mtu = att_mtu

    def to_c(self):
        ble_enable_params = driver.ble_enable_params_t()
        ble_enable_params.common_enable_params.p_conn_bw_counts = None
        ble_enable_params.common_enable_params.vs_uuid_count = self.vs_uuid_count
        ble_enable_params.gatts_enable_params.attr_tab_size = self.attr_tab_size
        ble_enable_params.gatts_enable_params.service_changed = self.service_changed
        ble_enable_params.gap_enable_params.periph_conn_count = self.periph_conn_count
        ble_enable_params.gap_enable_params.central_conn_count = self.central_conn_count
        ble_enable_params.gap_enable_params.central_sec_count = self.central_sec_count
        if nrf_sd_ble_api_ver >= 3:
            ble_enable_params.gatt_enable_params.att_mtu = self.att_mtu

        return ble_enable_params


class BLEVersion(object):
    def __init__(self, company_id, subversion_number, version_number, softdevice_info):
        self.company_id = company_id
        self.subversion_number = subversion_number
        self.version_number = version_number
        self.softdevice_info = softdevice_info

    @classmethod
    def _subversion_number_to_softdevice_info(cls, subversion_number):
        version = {
            0xA7: {"type": "s112", "major": 6, "minor": 0, "patch": 0},
            0xB0: {"type": "s112", "major": 6, "minor": 1, "patch": 0},
            0xB8: {"type": "s112", "major": 6, "minor": 1, "patch": 1},
            0x67: {"type": "s130", "major": 1, "minor": 0, "patch": 0},
            0x80: {"type": "s130", "major": 2, "minor": 0, "patch": 0},
            0x81: {"type": "s132", "major": 2, "minor": 0, "patch": 0},
            0x87: {"type": "s130", "major": 2, "minor": 0, "patch": 1},
            0x88: {"type": "s132", "major": 2, "minor": 0, "patch": 1},
            0x8C: {"type": "s132", "major": 3, "minor": 0, "patch": 0},
            0x91: {"type": "s132", "major": 3, "minor": 1, "patch": 0},
            0x95: {"type": "s132", "major": 4, "minor": 0, "patch": 0},
            0x98: {"type": "s132", "major": 4, "minor": 0, "patch": 2},
            0x99: {"type": "s132", "major": 4, "minor": 0, "patch": 3},
            0x9E: {"type": "s132", "major": 4, "minor": 0, "patch": 4},
            0x9F: {"type": "s132", "major": 4, "minor": 0, "patch": 5},
            0x9D: {"type": "s132", "major": 5, "minor": 0, "patch": 0},
            0xA5: {"type": "s132", "major": 5, "minor": 1, "patch": 0},
            0xA8: {"type": "s132", "major": 6, "minor": 0, "patch": 0},
            0xAF: {"type": "s132", "major": 6, "minor": 1, "patch": 0},
            0xB7: {"type": "s132", "major": 6, "minor": 1, "patch": 1},
            0xA9: {"type": "s140", "major": 6, "minor": 0, "patch": 0},
            0xAE: {"type": "s140", "major": 6, "minor": 1, "patch": 0},
            0xB6: {"type": "s140", "major": 6, "minor": 1, "patch": 1},
        }

        if subversion_number not in version:
            raise ValueError(
                "subversion_number %d does not map to a SoftDevice version",
                subversion_number,
            )

        return version[subversion_number]

    @classmethod
    def from_c(cls, ble_version):
        softdevice_info = cls._subversion_number_to_softdevice_info(
            ble_version.subversion_number
        )

        return cls(
            company_id=ble_version.company_id,
            subversion_number=ble_version.subversion_number,
            version_number=ble_version.version_number,
            softdevice_info=softdevice_info,
        )


class BLEGapAdvType(Enum):
    connectable_undirected = driver.BLE_GAP_ADV_TYPE_ADV_IND
    connectable_directed = driver.BLE_GAP_ADV_TYPE_ADV_DIRECT_IND
    scanable_undirected = driver.BLE_GAP_ADV_TYPE_ADV_SCAN_IND
    non_connectable_undirected = driver.BLE_GAP_ADV_TYPE_ADV_NONCONN_IND


class BLEGapRoles(Enum):
    invalid = driver.BLE_GAP_ROLE_INVALID
    periph = driver.BLE_GAP_ROLE_PERIPH
    central = driver.BLE_GAP_ROLE_CENTRAL


class BLEGapTimeoutSrc(Enum):
    advertising = driver.BLE_GAP_TIMEOUT_SRC_ADVERTISING
    if nrf_sd_ble_api_ver == 2:
        security_req = driver.BLE_GAP_TIMEOUT_SRC_SECURITY_REQUEST
    if nrf_sd_ble_api_ver == 5:
        auth_payload = driver.BLE_GAP_TIMEOUT_SRC_AUTH_PAYLOAD
    scan = driver.BLE_GAP_TIMEOUT_SRC_SCAN
    conn = driver.BLE_GAP_TIMEOUT_SRC_CONN


class BLEGapIOCaps(Enum):
    display_only = driver.BLE_GAP_IO_CAPS_DISPLAY_ONLY
    yesno = driver.BLE_GAP_IO_CAPS_DISPLAY_YESNO
    keyboard_only = driver.BLE_GAP_IO_CAPS_KEYBOARD_ONLY
    none = driver.BLE_GAP_IO_CAPS_NONE
    keyboard_display = driver.BLE_GAP_IO_CAPS_KEYBOARD_DISPLAY


class BLEGapSecStatus(EnumWithOffsets):
    success = driver.BLE_GAP_SEC_STATUS_SUCCESS
    timeout = driver.BLE_GAP_SEC_STATUS_TIMEOUT
    pdu_invalid = driver.BLE_GAP_SEC_STATUS_PDU_INVALID
    rfu_range1_begin = driver.BLE_GAP_SEC_STATUS_RFU_RANGE1_BEGIN
    rfu_range1_end = driver.BLE_GAP_SEC_STATUS_RFU_RANGE1_END
    passkey_entry_failed = driver.BLE_GAP_SEC_STATUS_PASSKEY_ENTRY_FAILED
    oob_not_available = driver.BLE_GAP_SEC_STATUS_OOB_NOT_AVAILABLE
    auth_req = driver.BLE_GAP_SEC_STATUS_AUTH_REQ
    confirm_value = driver.BLE_GAP_SEC_STATUS_CONFIRM_VALUE
    pairing_not_supp = driver.BLE_GAP_SEC_STATUS_PAIRING_NOT_SUPP
    enc_key_size = driver.BLE_GAP_SEC_STATUS_ENC_KEY_SIZE
    smp_cmd_unsupported = driver.BLE_GAP_SEC_STATUS_SMP_CMD_UNSUPPORTED
    unspecified = driver.BLE_GAP_SEC_STATUS_UNSPECIFIED
    repeated_attempts = driver.BLE_GAP_SEC_STATUS_REPEATED_ATTEMPTS
    invalid_params = driver.BLE_GAP_SEC_STATUS_INVALID_PARAMS
    dhkey_failure = driver.BLE_GAP_SEC_STATUS_DHKEY_FAILURE
    num_comp_failure = driver.BLE_GAP_SEC_STATUS_NUM_COMP_FAILURE
    br_edr_in_prog = driver.BLE_GAP_SEC_STATUS_BR_EDR_IN_PROG
    x_trans_key_disallowed = driver.BLE_GAP_SEC_STATUS_X_TRANS_KEY_DISALLOWED
    rfu_range2_begin = driver.BLE_GAP_SEC_STATUS_RFU_RANGE2_BEGIN
    rfu_range2_end = driver.BLE_GAP_SEC_STATUS_RFU_RANGE2_END


class BLEConfig(Enum):
    if nrf_sd_ble_api_ver == 5:
        conn_gap = driver.BLE_CONN_CFG_GAP
        conn_gattc = driver.BLE_CONN_CFG_GATTC
        conn_gatts = driver.BLE_CONN_CFG_GATTS
        conn_gatt = driver.BLE_CONN_CFG_GATT
        conn_l2cap = driver.BLE_CONN_CFG_L2CAP
        uuid_count = driver.BLE_COMMON_CFG_VS_UUID
        device_name = driver.BLE_GAP_CFG_DEVICE_NAME
        role_count = driver.BLE_GAP_CFG_ROLE_COUNT
        service_changed = driver.BLE_GATTS_CFG_SERVICE_CHANGED
        attr_tab_size = driver.BLE_GATTS_CFG_ATTR_TAB_SIZE


class BLEGapAdvParams(object):
    def __init__(self, interval_ms, timeout_s):
        self.interval_ms = interval_ms
        self.timeout_s = timeout_s

    def to_c(self):
        adv_params = driver.ble_gap_adv_params_t()
        adv_params.type = BLEGapAdvType.connectable_undirected.value
        adv_params.p_peer_addr = None  # Undirected advertisement.
        adv_params.fp = driver.BLE_GAP_ADV_FP_ANY
        adv_params.p_whitelist = None
        adv_params.interval = util.msec_to_units(self.interval_ms, util.UNIT_0_625_MS)
        adv_params.timeout = self.timeout_s

        return adv_params


class BLEGapScanParams(object):
    def __init__(self, interval_ms, window_ms, timeout_s):
        self.interval_ms = interval_ms
        self.window_ms = window_ms
        self.timeout_s = timeout_s

    def to_c(self):
        scan_params = driver.ble_gap_scan_params_t()
        scan_params.active = True
        scan_params.selective = False
        scan_params.p_whitelist = None
        scan_params.interval = util.msec_to_units(self.interval_ms, util.UNIT_0_625_MS)
        scan_params.window = util.msec_to_units(self.window_ms, util.UNIT_0_625_MS)
        scan_params.timeout = self.timeout_s

        return scan_params

class BLEGapConnSecMode(object):
    def __init__(self, sm=0, lv=0):
        self.sm = sm
        self.lv = lv
        
    def set_no_access(self):
        """BLE_GAP_CONN_SEC_MODE_SET_NO_ACCESS"""
        self.sm = 0
        self.lv = 0
        
    def set_open(self):
        """BLE_GAP_CONN_SEC_MODE_SET_OPEN"""
        self.sm = 1
        self.lv = 1
        
    def set_enc_no_mitm(self):
        """BLE_GAP_CONN_SEC_MODE_SET_ENC_NO_MITM"""
        self.sm = 1
        self.lv = 2
        
    def set_enc_with_mitm(self):
        """BLE_GAP_CONN_SEC_MODE_SET_ENC_WITH_MITM"""
        self.sm = 1
        self.lv = 3
        
    def set_lesc_enc_with_mitm(self): 
        """BLE_GAP_CONN_SEC_MODE_SET_LESC_ENC_WITH_MITM"""
        self.sm = 1
        self.lv = 4
    
    def set_signed_no_mitm(self):
        """BLE_GAP_CONN_SEC_MODE_SET_SIGNED_NO_MITM"""
        self.sm = 2
        self.lv = 1

    def set_signed_with_mitm(self):
        """BLE_GAP_CONN_SEC_MODE_SET_SIGNED_WITH_MITM"""
        self.sm = 2
        self.lv = 2

    @classmethod
    def from_c(cls, sec_mode):
        return cls(
            sm=sec_mode.sm,
            lv=sec_mode.lv,
        )
        
    def to_c(self):
        sec_mode = driver.ble_gap_conn_sec_mode_t()
        sec_mode.sm = self.sm
        sec_mode.lv = self.lv
        
        return sec_mode

    def __str__(self):
        return "sm({0.sm}) lv({0.lv}))".format(
            self
        )    

class BLEGapConnSec(object):
    def __init__(self, sec_mode, encr_key_size):
        assert isinstance(sec_mode, BLEGapConnSecMode), "Invalid argument type"
        self.sec_mode = sec_mode
        self.encr_key_size = encr_key_size

    @classmethod
    def from_c(cls, conn_sec):
        return cls(
            sec_mode=BLEGapConnSecMode.from_c(conn_sec.sec_mode),
            encr_key_size=conn_sec.encr_key_size,
        )

    def __str__(self):
        return "sec_mode({0.sec_mode}) encr_key_size({0.encr_key_size})".format(
            self
        )


class BLEGapConnParams(object):
    def __init__(
        self,
        min_conn_interval_ms,
        max_conn_interval_ms,
        conn_sup_timeout_ms,
        slave_latency,
    ):
        self.min_conn_interval_ms = min_conn_interval_ms
        self.max_conn_interval_ms = max_conn_interval_ms
        self.conn_sup_timeout_ms = conn_sup_timeout_ms
        self.slave_latency = slave_latency

    @classmethod
    def from_c(cls, conn_params):
        return cls(
            min_conn_interval_ms=util.units_to_msec(
                conn_params.min_conn_interval, util.UNIT_1_25_MS
            ),
            max_conn_interval_ms=util.units_to_msec(
                conn_params.max_conn_interval, util.UNIT_1_25_MS
            ),
            conn_sup_timeout_ms=util.units_to_msec(
                conn_params.conn_sup_timeout, util.UNIT_10_MS
            ),
            slave_latency=conn_params.slave_latency,
        )

    def to_c(self):
        conn_params = driver.ble_gap_conn_params_t()
        conn_params.min_conn_interval = util.msec_to_units(
            self.min_conn_interval_ms, util.UNIT_1_25_MS
        )
        conn_params.max_conn_interval = util.msec_to_units(
            self.max_conn_interval_ms, util.UNIT_1_25_MS
        )
        conn_params.conn_sup_timeout = util.msec_to_units(
            self.conn_sup_timeout_ms, util.UNIT_10_MS
        )
        conn_params.slave_latency = self.slave_latency
        return conn_params

    def __str__(self):
        return (
            "Connection Parameters min_conn_interval_ms({0.min_conn_interval_ms}) "
            "max_conn_interval_ms({0.max_conn_interval_ms}) conn_sup_timeout_ms({0.conn_sup_timeout_ms}) "
            "slave_latency({0.slave_latency})"
        ).format(self)


class BLEGapAddr(object):
    class Types(Enum):
        public = driver.BLE_GAP_ADDR_TYPE_PUBLIC
        random_static = driver.BLE_GAP_ADDR_TYPE_RANDOM_STATIC
        random_private_resolvable = driver.BLE_GAP_ADDR_TYPE_RANDOM_PRIVATE_RESOLVABLE
        random_private_non_resolvable = (
            driver.BLE_GAP_ADDR_TYPE_RANDOM_PRIVATE_NON_RESOLVABLE
        )
        anonymous = 0x7F  # driver.BLE_GAP_ADDR_TYPE_ANONYMOUS, available from SD v6

    def __init__(self, addr_type, addr):
        assert type(addr_type) in [BLEGapAddr.Types, int], "Invalid addr_type: {addr_type}"
        self.addr_type = addr_type
        self.addr = addr

    def __getstate__(self):
        self.addr_type = self.addr_type.value
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        self.addr_type = BLEGapAddr.Types(self.addr_type)

    @classmethod
    def from_c(cls, addr):
        addr_list = util.uint8_array_to_list(addr.addr, driver.BLE_GAP_ADDR_LEN)
        addr_list.reverse()
        if addr.addr_type in BLEGapAddr.Types.__members__.items():
            addr_type = BLEGapAddr.Types(addr.addr_type)
        else:
            addr_type = addr.addr_type
        return cls(addr_type=addr_type, addr=addr_list)

    def to_c(self):
        addr_array = util.list_to_uint8_array(self.addr[::-1])
        addr = driver.ble_gap_addr_t()
        if type(self.addr_type) == BLEGapAddr.Types:
            addr.addr_type = self.addr_type.value
        else:
            addr.addr_type = self.addr_type
        addr.addr = addr_array.cast()
        return addr


class BLEGapSecKeyset(object):
    def __init__(self, keys_own, keys_peer):
        self.keys_own = keys_own
        self.keys_peer = keys_peer

    @classmethod
    def from_c(cls, keyset):
        return cls(
            keys_own=BLEGapSecKeys.from_c(keyset.keys_own),
            keys_peer=BLEGapSecKeys.from_c(keyset.keys_peer),
        )

    def to_c(self):
        keyset = driver.ble_gap_sec_keyset_t()
        keyset.keys_own = BLEGapSecKeys(
            self.keys_own.p_enc_key,
            self.keys_own.p_id_key,
            self.keys_own.p_sign_key,
            self.keys_own.p_pk
        ).to_c()
        keyset.keys_peer = BLEGapSecKeys(
            self.keys_peer.p_enc_key,
            self.keys_peer.p_id_key,
            self.keys_peer.p_sign_key,
            self.keys_peer.p_pk
        ).to_c()

        return keyset

    def __str__(self):
        return "keys_own({0.keys_own}) keys_peer({0.keys_peer})".format(self)


class BLEGapSecKeys(object):
    def __init__(self, enc_key, id_key, sign_key, pk):
        self.enc_key = enc_key
        self.id_key = id_key
        self.sign_key = sign_key
        self.pk = pk

    @classmethod
    def from_c(cls, keys):
        return cls(
            enc_key=BLEGapEncKey.from_c(keys.p_enc_key),
            id_key=BLEGapIdKey.from_c(keys.p_id_key),
            sign_key=BLEGapSignInfo.from_c(keys.p_sign_key),
            pk=BLEGapLescP256Pk.from_c(keys.p_pk)
        )

    def to_c(self):
        sec_keys = driver.ble_gap_sec_keys_t()
        sec_keys.p_enc_key = BLEGapEncKey(self.enc_key.master_id, self.enc_key.enc_info).to_c()
        sec_keys.p_id_key = BLEGapIdKey(self.id_key.id_info, self.id_key.id_info).to_c()
        sec_keys.p_sign_key = BLEGapSignInfo(self.sign_key.csrk).to_c()
        sec_keys.p_pk = BLEGapLescP256Pk(self.pk.pk).to_c()
        return sec_keys

    def __str__(self):
        return "enc_key({0.p_enc_key}) id_key({0.p_id_key}) csrk({0.p_csrk}) pk({0.p_pk})".format(
            self
        )


class BLEGapLescP256Pk(object):
    def __init__(self, pk):
        self.pk = pk

    @classmethod
    def from_c(cls, p_pk):
        return cls(
            pk=util.uint8_array_to_list(p_pk.pk, driver.BLE_GAP_LESC_P256_PK_LEN)
        )

    def to_c(self):
        lescp256pk_array = util.list_to_uint8_array(self.pk)
        lescp256pk = driver.ble_gap_lesc_p256_pk_t()
        lescp256pk.pk = lescp256pk_array.cast()
        return lescp256pk

    def __str__(self):
        return ("pk({0.pk}))").format(self)


class BLEGapDHKey(object):
    def __init__(self, key):
        self.key=key

    def to_c(self):
        key_array = util.list_to_uint8_array(self.key)
        dh_key = driver.ble_gap_lesc_dhkey_t()
        dh_key.key = key_array.cast()
        return dh_key

    def __str__(self):
        return ("p_dhkey({0.p_dhkey}))").format(self)


class BLEGapEncKey(object):
    def __init__(self, master_id, enc_info):
        self.master_id = master_id
        self.enc_info = enc_info

    @classmethod
    def from_c(cls, enc_key):
        return cls(
            master_id=BLEGapMasterId.from_c(enc_key.master_id),
            enc_info=BLEGapEncInfo.from_c(enc_key.enc_info),
        )

    def to_c(self):
        enc_key = driver.ble_gap_enc_key_t()
        enk_key.master_id = BLEGapMasterId(self.master_id).to_c()
        enk_key.enc_info = BLEGapEncInfo(self.enc_info).to_c()
        return enc_key

    def __str__(self):
        return "master_id({0.master_id}) enc_info({0.enc_info})".format(self)


class BLEGapIdKey(object):
    def __init__(self, id_info, id_addr_info):
        self.irk = id_info
        self.id_addr_info = id_addr_info
        assert isinstance(id_addr_info, BLEGapAddr), 'Invalid argument type'

    @classmethod
    def from_c(cls, id_key):
        return cls(
            id_info=util.uint8_array_to_list(id_key.id_info.irk, driver.BLE_GAP_SEC_KEY_LEN),
            id_addr_info=BLEGapAddr.from_c(id_key.id_addr_info)
        )

    def to_c(self):
        id_key = driver.ble_gap_id_key_t()
        irk_array = util.list_to_uint8_array(self.irk)
        irk = driver.ble_gap_irk_t()
        irk.irk = irk_array.cast()
        id_key.id_info = irk
        id_key.id_addr_info = self.id_addr_info.to_c()
        return id_key

    def __str__(self):
        return ("irk({0.irk}) id_addr_info({0.id_addr_info})").format(self)


class BLEGapEncInfo(object):
    def __init__(self, ltk, auth, lesc, ltk_len):
        self.ltk = ltk
        self.auth = auth
        self.lesc = lesc
        self.ltk_len = ltk_len

    @classmethod
    def from_c(cls, enc_info):
        ltk_list = util.uint8_array_to_list(enc_info.ltk, driver.BLE_GAP_SEC_KEY_LEN)
        return cls(
            ltk=ltk_list,
            auth=enc_info.auth,
            lesc=enc_info.lesc,
            ltk_len=enc_info.ltk_len,
        )

    def to_c(self):
        ltk_array = util.list_to_uint8_array(self.ltk)
        enc_info = driver.ble_gap_enc_info_t()
        enc_info.auth = self.auth
        enc_info.lesc = self.lesc
        enc_info.ltk_len = self.ltk_len
        enc_info.ltk = ltk_array.cast()
        return enc_info

    def __str__(self):
        return "ltk({0.ltk}) auth({0.auth}) lesc({0.lesc}) ltk_len({0.ltk_len})".format(
            self
        )


class BLEGapSignInfo(object):
    def __init__(self, csrk):
        self.csrk = csrk

    @classmethod
    def from_c(cls, sign_info):
        csrk_list = util.uint8_array_to_list(sign_info.csrk, driver.BLE_GAP_SEC_KEY_LEN)
        return cls(
            csrk=csrk_list
        )

    def to_c(self):
        csrk_array = util.list_to_uint8_array(self.csrk)
        sign_info = driver.ble_gap_sign_info_t()
        sign_info.csrk = csrk_array.cast()
        return sign_info

    def __str__(self):
        return "csrk({0.csrk}))".format(
            self
        )


class BLEGapMasterId(object):
    def __init__(self, ediv, rand):
        self.ediv = ediv
        self.rand = rand

    @classmethod
    def from_c(cls, master_id):
        rand_list = util.uint8_array_to_list(
            master_id.rand, driver.BLE_GAP_SEC_RAND_LEN
        )
        return cls(ediv=master_id.ediv, rand=rand_list)

    def to_c(self):
        rand_array = util.list_to_uint8_array(self.rand)
        master_id = driver.ble_gap_master_id_t()
        master_id.ediv = self.ediv
        master_id.rand = rand_array.cast()
        return master_id

    def __str__(self):
        return "ediv({0.ediv}) rand({0.rand})".format(self)


class BLEGapSecKDist(object):
    def __init__(self, enc, id, sign, link):
        self.enc = enc
        self.id = id
        self.sign = sign
        self.link = link

    @classmethod
    def from_c(cls, kdist):
        return cls(enc=kdist.enc, id=kdist.id, sign=kdist.sign, link=kdist.link)

    def to_c(self):
        kdist = driver.ble_gap_sec_kdist_t()
        kdist.enc = self.enc
        kdist.id = self.id
        kdist.sign = self.sign
        kdist.link = self.link
        return kdist

    def __str__(self):
        return "enc({0.enc}) id({0.id}) sign({0.sign}) link({0.link})".format(self)


class BLEGapSecLevels(object):
    def __init__(self, lv1, lv2, lv3, lv4):
        self.lv1 = lv1
        self.lv2 = lv2
        self.lv3 = lv3
        self.lv4 = lv4

    @classmethod
    def from_c(cls, sm_levels):
        return cls(lv1=sm_levels.lv1,
                   lv2=sm_levels.lv2,
                   lv3=sm_levels.lv3,
                   lv4=sm_levels.lv4)

    def to_c(self):
        sm_levels = driver.ble_gap_sec_levels_t()
        sm_levels.lv1 = self.lv1
        sm_levels.lv2 = self.lv2
        sm_levels.lv3 = self.lv3
        sm_levels.lv4 = self.lv4
        return sm_levels

    def __str__(self):
        return ("lv1({0.lv1}) lv2({0.lv2}) lv3({0.lv3}) lv4({0.lv4})").format(self)


class BLEGapSecParams(object):
    def __init__(
        self,
        bond,
        mitm,
        lesc,
        keypress,
        io_caps,
        oob,
        min_key_size,
        max_key_size,
        kdist_own,
        kdist_peer,
    ):
        assert isinstance(kdist_own, BLEGapSecKDist), "Invalid argument type"
        assert isinstance(kdist_peer, BLEGapSecKDist), "Invalid argument type"
        assert isinstance(io_caps, BLEGapIOCaps), "Invalid argument type"
        self.bond = bond
        self.mitm = mitm
        self.lesc = lesc
        self.keypress = keypress
        self.io_caps = io_caps
        self.oob = oob
        self.max_key_size = max_key_size
        self.min_key_size = min_key_size
        self.kdist_own = kdist_own
        self.kdist_peer = kdist_peer

    @classmethod
    def from_c(cls, params):
        return cls(
            bond=params.bond,
            mitm=params.mitm,
            lesc=params.lesc,
            keypress=params.keypress,
            io_caps=BLEGapIOCaps(params.io_caps),
            oob=params.oob,
            min_key_size=params.min_key_size,
            max_key_size=params.max_key_size,
            kdist_own=BLEGapSecKDist.from_c(params.kdist_own),
            kdist_peer=BLEGapSecKDist.from_c(params.kdist_peer),
        )

    def to_c(self):
        params = driver.ble_gap_sec_params_t()
        params.bond = self.bond
        params.mitm = self.mitm
        params.lesc = self.lesc
        params.keypress = self.keypress
        params.io_caps = self.io_caps.value
        params.oob = self.oob
        params.max_key_size = self.max_key_size
        params.min_key_size = self.min_key_size
        params.kdist_own = self.kdist_own.to_c()
        params.kdist_peer = self.kdist_peer.to_c()
        return params

    def __str__(self):
        return (
            "Security Parameters bond({0.bond}) mitm({0.mitm}) lesc({0.lesc}) keypress({0.keypress}) "
            "io_caps({0.io_caps}) oob({0.oob}) max_key_size({0.max_key_size}) "
            "min_key_size({0.min_key_size}) kdist_own({0.kdist_own}) kdist_peer({0.kdist_peer})"
        ).format(self)


class BLEGapPrivacyParams(object):
    def __init__(self, privacy_mode, private_addr_type, private_addr_cycle_s, irk):
        self.privacy_mode = privacy_mode
        self.private_addr_type = private_addr_type
        self.private_addr_cycle_s = private_addr_cycle_s
        self.irk = irk

    @classmethod
    def from_c(cls, priv_params):
        irk_list = util.uint8_array_to_list(priv_params.irk.irk, 16)
        return cls(
            privacy_mode=priv_params.privacy_mode,
            private_addr_type=priv_params.private_addr_type,
            private_addr_cycle_s=priv_params.private_addr_cycle_s,
            irk=irk_list,
        )

    def to_c(self):
        priv_params = driver.ble_gap_privacy_params_t()
        priv_params.privacy_mode = self.privacy_mode
        priv_params.private_addr_type = self.private_addr_type
        priv_params.private_addr_cycle_s = self.private_addr_cycle_s
        if self.irk:
            irk_array = util.list_to_uint8_array(self.irk)
            irk = driver.ble_gap_irk_t()
            irk.irk = irk_array.cast()
            priv_params.p_device_irk = irk

        return priv_params

    def __str__(self):
        return (
            "privacy_mode({0.privacy_mode}) private_addr_type({0.private_addr_type}) "
            "private_addr_cycle_s({0.private_addr_cycle_s}) irk({0.irk})"
        ).format(self)


class BLEGapPasskeyDisplay(object):
    def __init__(self, passkey):
        self.passkey = passkey

    @classmethod
    def from_c(cls, params):
        return cls(
            passkey=util.uint8_array_to_list(params.passkey, 6)
        )


class BLEAdvData(object):
    class Types(Enum):
        flags = driver.BLE_GAP_AD_TYPE_FLAGS
        service_16bit_uuid_more_available = (
            driver.BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_MORE_AVAILABLE
        )
        service_16bit_uuid_complete = driver.BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_COMPLETE
        service_32bit_uuid_more_available = (
            driver.BLE_GAP_AD_TYPE_32BIT_SERVICE_UUID_MORE_AVAILABLE
        )
        service_32bit_uuid_complete = driver.BLE_GAP_AD_TYPE_32BIT_SERVICE_UUID_COMPLETE
        service_128bit_uuid_more_available = (
            driver.BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_MORE_AVAILABLE
        )
        service_128bit_uuid_complete = (
            driver.BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_COMPLETE
        )
        short_local_name = driver.BLE_GAP_AD_TYPE_SHORT_LOCAL_NAME
        complete_local_name = driver.BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME
        tx_power_level = driver.BLE_GAP_AD_TYPE_TX_POWER_LEVEL
        class_of_device = driver.BLE_GAP_AD_TYPE_CLASS_OF_DEVICE
        simple_pairing_hash_c = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_HASH_C
        simple_pairing_randimizer_r = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_RANDOMIZER_R
        security_manager_tk_value = driver.BLE_GAP_AD_TYPE_SECURITY_MANAGER_TK_VALUE
        security_manager_oob_flags = driver.BLE_GAP_AD_TYPE_SECURITY_MANAGER_OOB_FLAGS
        slave_connection_interval_range = (
            driver.BLE_GAP_AD_TYPE_SLAVE_CONNECTION_INTERVAL_RANGE
        )
        solicited_sevice_uuids_16bit = (
            driver.BLE_GAP_AD_TYPE_SOLICITED_SERVICE_UUIDS_16BIT
        )
        solicited_sevice_uuids_128bit = (
            driver.BLE_GAP_AD_TYPE_SOLICITED_SERVICE_UUIDS_128BIT
        )
        service_data = driver.BLE_GAP_AD_TYPE_SERVICE_DATA
        public_target_address = driver.BLE_GAP_AD_TYPE_PUBLIC_TARGET_ADDRESS
        random_target_address = driver.BLE_GAP_AD_TYPE_RANDOM_TARGET_ADDRESS
        appearance = driver.BLE_GAP_AD_TYPE_APPEARANCE
        advertising_interval = driver.BLE_GAP_AD_TYPE_ADVERTISING_INTERVAL
        le_bluetooth_device_address = driver.BLE_GAP_AD_TYPE_LE_BLUETOOTH_DEVICE_ADDRESS
        le_role = driver.BLE_GAP_AD_TYPE_LE_ROLE
        simple_pairng_hash_c256 = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_HASH_C256
        simple_pairng_randomizer_r256 = (
            driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_RANDOMIZER_R256
        )
        service_data_32bit_uuid = driver.BLE_GAP_AD_TYPE_SERVICE_DATA_32BIT_UUID
        service_data_128bit_uuid = driver.BLE_GAP_AD_TYPE_SERVICE_DATA_128BIT_UUID
        uri = driver.BLE_GAP_AD_TYPE_URI
        information_3d_data = driver.BLE_GAP_AD_TYPE_3D_INFORMATION_DATA
        manufacturer_specific_data = driver.BLE_GAP_AD_TYPE_MANUFACTURER_SPECIFIC_DATA

        # Additional official AD types from
        # https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile/
        indoor_positioning = 0x25
        transport_discovery_data = 0x26
        le_supported_features = 0x27
        channel_map_update_indication = 0x28
        pb_adv = 0x29
        mesh_message = 0x2A
        mesh_beacon = 0x2B
        biginfo = 0x2C
        broadcast_code = 0x2D

    def __init__(self, **kwargs):
        self.records = dict()
        for k in kwargs:
            self.records[BLEAdvData.Types[k]] = kwargs[k]
        self.__data_array = None

    def __getstate__(self):
        self.records = {k.value: v for k, v in self.records.items()}
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        self.records = {BLEAdvData.Types(k): v for k, v in self.records.items()}

    def to_c(self):
        data_list = list()
        for k in self.records:
            data_list.append(len(self.records[k]) + 1)  # add type length
            data_list.append(k.value)
            if isinstance(self.records[k], str):
                data_list.extend([ord(c) for c in self.records[k]])

            elif isinstance(self.records[k], list):
                data_list.extend(self.records[k])

            else:
                raise NordicSemiException(
                    "Unsupported value type: 0x{:02X}".format(type(self.records[k]))
                )

        data_len = len(data_list)
        if data_len == 0:
            return data_len, None
        else:
            self.__data_array = util.list_to_uint8_array(data_list)
            return data_len, self.__data_array.cast()

    @classmethod
    def from_c(cls, adv_report_evt):
        ad_list = util.uint8_array_to_list(adv_report_evt.data, adv_report_evt.dlen)
        ble_adv_data = cls()
        index = 0

        ad_len = None
        ad_type = None

        while index < len(ad_list):
            try:
                ad_len = ad_list[index]
                if ad_len == 0:
                    logger.info(f"ad_len is zero, discarding rest of ad_list")
                    return ble_adv_data

                ad_type = ad_list[index + 1]
                offset = index + 2
                key = BLEAdvData.Types(ad_type)
                ble_adv_data.records[key] = ad_list[offset: offset + ad_len - 1]
            except ValueError:
                if ad_type:
                    logger.info(
                        "Unknown advertising data type: 0x{:02X}".format(ad_type)
                    )
                else:
                    logger.info("Invalid advertising data")
            except IndexError:
                logger.info("Invalid advertising data: {}".format(ad_list))
                return ble_adv_data

            if ad_len:
                index += ad_len + 1

        return ble_adv_data


class BLEGattWriteOperation(Enum):
    invalid = driver.BLE_GATT_OP_INVALID
    write_req = driver.BLE_GATT_OP_WRITE_REQ
    write_cmd = driver.BLE_GATT_OP_WRITE_CMD
    singed_write_cmd = driver.BLE_GATT_OP_SIGN_WRITE_CMD
    prepare_write_req = driver.BLE_GATT_OP_PREP_WRITE_REQ
    execute_write_req = driver.BLE_GATT_OP_EXEC_WRITE_REQ


class BLEGattHVXType(Enum):
    invalid = driver.BLE_GATT_HVX_INVALID
    notification = driver.BLE_GATT_HVX_NOTIFICATION
    indication = driver.BLE_GATT_HVX_INDICATION


class BLEGattStatusCode(EnumWithOffsets):
    success = driver.BLE_GATT_STATUS_SUCCESS
    unknown = driver.BLE_GATT_STATUS_UNKNOWN
    invalid = driver.BLE_GATT_STATUS_ATTERR_INVALID
    invalid_handle = driver.BLE_GATT_STATUS_ATTERR_INVALID_HANDLE
    read_not_permitted = driver.BLE_GATT_STATUS_ATTERR_READ_NOT_PERMITTED
    write_not_permitted = driver.BLE_GATT_STATUS_ATTERR_WRITE_NOT_PERMITTED
    invalid_pdu = driver.BLE_GATT_STATUS_ATTERR_INVALID_PDU
    insuf_authentication = driver.BLE_GATT_STATUS_ATTERR_INSUF_AUTHENTICATION
    req_not_supp = driver.BLE_GATT_STATUS_ATTERR_REQUEST_NOT_SUPPORTED
    invalid_offs = driver.BLE_GATT_STATUS_ATTERR_INVALID_OFFSET
    insuf_authorization = driver.BLE_GATT_STATUS_ATTERR_INSUF_AUTHORIZATION
    prep_q_full = driver.BLE_GATT_STATUS_ATTERR_PREPARE_QUEUE_FULL
    attribute_not_found = driver.BLE_GATT_STATUS_ATTERR_ATTRIBUTE_NOT_FOUND
    attribute_not_long = driver.BLE_GATT_STATUS_ATTERR_ATTRIBUTE_NOT_LONG
    insuf_enc_key_size = driver.BLE_GATT_STATUS_ATTERR_INSUF_ENC_KEY_SIZE
    invalid_att_va_length = driver.BLE_GATT_STATUS_ATTERR_INVALID_ATT_VAL_LENGTH
    unlikely_error = driver.BLE_GATT_STATUS_ATTERR_UNLIKELY_ERROR
    insuf_encryption = driver.BLE_GATT_STATUS_ATTERR_INSUF_ENCRYPTION
    unsupp_group_type = driver.BLE_GATT_STATUS_ATTERR_UNSUPPORTED_GROUP_TYPE
    insuf_resources = driver.BLE_GATT_STATUS_ATTERR_INSUF_RESOURCES
    rfu_range1_begin = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE1_BEGIN
    rfu_range1_end = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE1_END
    app_begin = driver.BLE_GATT_STATUS_ATTERR_APP_BEGIN
    app_end = driver.BLE_GATT_STATUS_ATTERR_APP_END
    rfu_range2_begin = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE2_BEGIN
    rfu_range2_end = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE2_END
    rfu_range3_begin = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE3_BEGIN
    rfu_range3_end = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE3_END
    cccd_config_error = driver.BLE_GATT_STATUS_ATTERR_CPS_CCCD_CONFIG_ERROR
    procedure_in_progress = driver.BLE_GATT_STATUS_ATTERR_CPS_PROC_ALR_IN_PROG
    cps_out_of_range = driver.BLE_GATT_STATUS_ATTERR_CPS_OUT_OF_RANGE


class BLEGattExecWriteFlag(Enum):
    prepared_cancel = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_CANCEL
    prepared_write = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_WRITE
    unused = 0x00


class BLEGattcWriteParams(object):
    def __init__(self, write_op, flags, handle, data, offset):
        assert isinstance(write_op, BLEGattWriteOperation), "Invalid argument type"
        assert isinstance(flags, BLEGattExecWriteFlag), "Invalid argument type"
        self.write_op = write_op
        self.flags = flags
        self.handle = handle
        self.data = data
        self.offset = offset
        self.__data_array = None

    @classmethod
    def from_c(cls, gattc_write_params):
        return cls(
            write_op=BLEGattWriteOperation(gattc_write_params.write_op),
            flags=gattc_write_params.flags,
            handle=gattc_write_params.handle,
            data=util.uint8_array_to_list(
                gattc_write_params.p_value, gattc_write_params.len
            ),
            offset=gattc_write_params.offset,
        )

    def to_c(self):
        self.__data_array = util.list_to_uint8_array(self.data)
        write_params = driver.ble_gattc_write_params_t()
        write_params.p_value = self.__data_array.cast()
        write_params.flags = self.flags.value
        write_params.handle = self.handle
        write_params.offset = self.offset
        write_params.len = len(self.data)
        write_params.write_op = self.write_op.value

        return write_params

    def __str__(self):
        return (
            "Write Params write_op({0.write_op}) flags({0.flags})"
            " handle({0.handle}) offset({0.offset}) data({0.data})"
        ).format(self)


class BLEHci(Enum):
    success = driver.BLE_HCI_STATUS_CODE_SUCCESS
    unknown_btle_command = driver.BLE_HCI_STATUS_CODE_UNKNOWN_BTLE_COMMAND
    unknown_connection_identifier = (
        driver.BLE_HCI_STATUS_CODE_UNKNOWN_CONNECTION_IDENTIFIER
    )
    authentication_failure = driver.BLE_HCI_AUTHENTICATION_FAILURE
    pin_or_key_missing = driver.BLE_HCI_STATUS_CODE_PIN_OR_KEY_MISSING
    memory_capacity_exceeded = driver.BLE_HCI_MEMORY_CAPACITY_EXCEEDED
    connection_timeout = driver.BLE_HCI_CONNECTION_TIMEOUT
    command_disallowed = driver.BLE_HCI_STATUS_CODE_COMMAND_DISALLOWED
    invalid_btle_command_parameters = (
        driver.BLE_HCI_STATUS_CODE_INVALID_BTLE_COMMAND_PARAMETERS
    )
    remote_user_terminated_connection = driver.BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION
    remote_dev_termination_due_to_low_resources = (
        driver.BLE_HCI_REMOTE_DEV_TERMINATION_DUE_TO_LOW_RESOURCES
    )
    remote_dev_termination_due_to_power_off = (
        driver.BLE_HCI_REMOTE_DEV_TERMINATION_DUE_TO_POWER_OFF
    )
    local_host_terminated_connection = driver.BLE_HCI_LOCAL_HOST_TERMINATED_CONNECTION
    unsupported_remote_feature = driver.BLE_HCI_UNSUPPORTED_REMOTE_FEATURE
    invalid_lmp_parameters = driver.BLE_HCI_STATUS_CODE_INVALID_LMP_PARAMETERS
    unspecified_error = driver.BLE_HCI_STATUS_CODE_UNSPECIFIED_ERROR
    lmp_response_timeout = driver.BLE_HCI_STATUS_CODE_LMP_RESPONSE_TIMEOUT
    lmp_pdu_not_allowed = driver.BLE_HCI_STATUS_CODE_LMP_PDU_NOT_ALLOWED
    instant_passed = driver.BLE_HCI_INSTANT_PASSED
    pairintg_with_unit_key_unsupported = (
        driver.BLE_HCI_PAIRING_WITH_UNIT_KEY_UNSUPPORTED
    )
    differen_transaction_collision = driver.BLE_HCI_DIFFERENT_TRANSACTION_COLLISION
    controller_busy = driver.BLE_HCI_CONTROLLER_BUSY
    conn_interval_unacceptable = driver.BLE_HCI_CONN_INTERVAL_UNACCEPTABLE
    directed_advertiser_timeout = driver.BLE_HCI_DIRECTED_ADVERTISER_TIMEOUT
    conn_terminated_due_to_mic_failure = (
        driver.BLE_HCI_CONN_TERMINATED_DUE_TO_MIC_FAILURE
    )
    conn_failed_to_be_established = driver.BLE_HCI_CONN_FAILED_TO_BE_ESTABLISHED


class BLEUUIDBase(object):
    def __init__(self, vs_uuid_base=None, uuid_type=None):
        assert isinstance(vs_uuid_base, (list, type(None))), "Invalid argument type"
        assert isinstance(uuid_type, (int, type(None))), "Invalid argument type"
        if (vs_uuid_base is None) and uuid_type is None:
            self.base = [
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x10,
                0x00,
                0x80,
                0x00,
                0x00,
                0x80,
                0x5F,
                0x9B,
                0x34,
                0xFB,
            ]
            self.type = driver.BLE_UUID_TYPE_BLE

        else:
            self.base = vs_uuid_base
            self.type = uuid_type

        self.__array = None

    @classmethod
    def from_c(cls, uuid):
        return cls(uuid_type=uuid.type)

    def to_c(self):
        lsb_list = self.base[::-1]
        self.__array = util.list_to_uint8_array(lsb_list)
        uuid = driver.ble_uuid128_t()
        uuid.uuid128 = self.__array.cast()
        return uuid


class BLEUUID(object):
    class Standard(Enum):
        unknown = 0x0000
        service_primary = 0x2800
        service_secondary = 0x2801
        characteristic = 0x2803
        cccd = 0x2902
        battery_level = 0x2A19
        heart_rate = 0x2A37

    def __init__(self, value, base=BLEUUIDBase()):
        assert isinstance(base, BLEUUIDBase), "Invalid argument type"
        self.base = base
        try:
            self.value = (
                value
                if isinstance(value, BLEUUID.Standard)
                else BLEUUID.Standard(value)
            )
        except ValueError:
            self.value = value

    def __setstate__(self, state):
        try:
            self.value = BLEUUID.Standard(state["value"])
        except ValueError:
            self.value = state["value"]
        self.base = state["base"]

    def __getstate__(self):
        if isinstance(self.value, BLEUUID.Standard):
            return {"value": self.value.value, "base": self.base}
        return {"value": self.value, "base": self.base}

    def __str__(self):
        if isinstance(self.value, BLEUUID.Standard):
            return "0x{:04X} ({})".format(self.value.value, self.value)
        else:
            return "0x{:04X}".format(self.value)

    def __repr__(self):
        if isinstance(self.value, BLEUUID.Standard):
            return "<BLEUUID obj: 0x{:04X} ({})>".format(self.value.value, self.value)
        else:
            return "<BLEUUID obj: 0x{:04X}>".format(self.value)

    def __eq__(self, other):
        if not isinstance(other, BLEUUID):
            return False
        return (self.value == other.value) and (self.base.type == other.base.type) and \
            (self.base.base is None or other.base.base is None or self.base.base == other.base.base)

    def __hash__(self):
        return hash(self.value * (self.base.type or 1))

    @classmethod
    def from_c(cls, uuid):
        return cls(value=uuid.uuid, base=BLEUUIDBase.from_c(uuid))

    def to_c(self):
        assert self.base.type is not None, "Vendor specific UUID not registered"
        uuid = driver.ble_uuid_t()
        if isinstance(self.value, BLEUUID.Standard):
            uuid.uuid = self.value.value
        else:
            uuid.uuid = self.value
        uuid.type = self.base.type
        return uuid


class BLEGattHandle(object):
    def __init__(self, handle=driver.BLE_GATT_HANDLE_INVALID):
        self.handle = handle


class BLEGattCharProps(object):
    def __init__(self, broadcast=False, read=False,
                 write_wo_resp=False, write=False,
                 notify=False, indicate=False,
                 auth_signed_wr=False):
        self.broadcast = broadcast
        self.read = read
        self.write_wo_resp = write_wo_resp
        self.write = write
        self.notify = notify
        self.indicate = indicate
        self.auth_signed_wr = auth_signed_wr

    def to_c(self):
        params = driver.ble_gatt_char_props_t()
        params.broadcast = int(self.broadcast)
        params.read = int(self.read)
        params.write_wo_resp = int(self.write_wo_resp)
        params.write = int(self.write)
        params.notify = int(self.notify)
        params.indicate = int(self.indicate)
        params.auth_signed_wr = int(self.auth_signed_wr)
        return params


class BLEGattsAttrMD(object):
    def __init__(self, vloc=driver.BLE_GATTS_VLOC_STACK,
                 rd_auth=False, wr_auth=False, 
                 read_perm=None, write_perm=None, vlen=1):
        self.vloc = vloc
        self.rd_auth = rd_auth
        self.wr_auth = wr_auth
        self.read_perm = read_perm
        self.write_perm = write_perm
        self.vlen = vlen

    def to_c(self):
        attr_md = driver.ble_gatts_attr_md_t()
        attr_md.vloc = self.vloc
        if self.read_perm:
            attr_md.read_perm = self.read_perm.to_c()
        if self.write_perm:
            attr_md.write_perm = self.write_perm.to_c()
        attr_md.rd_auth = int(self.rd_auth)
        attr_md.wr_auth = int(self.wr_auth)
        attr_md.vlen = self.vlen
        return attr_md


class BLEGattsAttr(object):
    def __init__(self, uuid, attr_md, max_len, init_offs=0, value=[]):
        assert isinstance(uuid, BLEUUID)
        assert isinstance(attr_md, BLEGattsAttrMD)
        self.uuid = uuid
        self.attr_md = attr_md
        self.max_len = max_len
        self.init_offs = init_offs
        self.value = value

    def to_c(self):
        self.data_array = util.list_to_uint8_array(self.value)
        attr = driver.ble_gatts_attr_t()
        attr.p_uuid = self.uuid.to_c()
        attr.p_attr_md = self.attr_md.to_c()
        attr.max_len = self.max_len
        if self.value:
            attr.init_len = len(self.value)
            attr.init_offs = self.init_offs
            attr.p_value = self.data_array.cast()
        return attr


class BLEGattsHVXParams(object):
    def __init__(self, handle, hvx_type, data, offset=0):
        assert isinstance(handle, BLEGattsCharHandles)
        self.handle = handle
        self.type = hvx_type
        self.offset = offset
        self.data = data

    def to_c(self):
        hvx_params = driver.ble_gatts_hvx_params_t()

        self._len_ptr = driver.new_uint16()
        if self.data:
            self.data_array = util.list_to_uint8_array(self.data)
            hvx_params.p_data = self.data_array.cast()
            driver.uint16_assign(self._len_ptr, len(self.data))
        else:
            driver.uint16_assign(self._len_ptr, 0)
        hvx_params.handle = self.handle.value_handle
        hvx_params.type = self.type
        hvx_params.offset = self.offset
        hvx_params.p_len = self._len_ptr
        return hvx_params


class BLEGattsCharHandles(object):
    def __init__(self, value_handle=0, user_desc_handle=0,
                 cccd_handle=0, sccd_handle=0):
        self.value_handle = value_handle
        self.user_desc_handle = user_desc_handle
        self.cccd_handle = cccd_handle
        self.sccd_handle = sccd_handle

    def to_c(self):
        char_handles = driver.ble_gatts_char_handles_t()
        char_handles.value_handle = self.value_handle
        char_handles.user_desc_handle = self.user_desc_handle
        char_handles.cccd_handle = self.cccd_handle
        char_handles.sccd_handle = self.sccd_handle
        return char_handles


class BLEGattsCharMD(object):
    def __init__(self, char_props, user_desc=None, pf=None,
                 desc_md=None, cccd_md=None, sccd_md=None):
        assert isinstance(char_props, BLEGattCharProps)
        self.char_props = char_props
        self.user_desc = user_desc
        self.pf = pf
        self.desc_md = desc_md
        self.cccd_md = cccd_md
        self.sccd_md = sccd_md

    def __str__(self):
        return str(self.__dict__)

    def to_c(self):
        char_md = driver.ble_gatts_char_md_t()
        char_md.char_props = self.char_props.to_c()
        if self.user_desc:
            user_desc_array=util.list_to_uint8_array(self.user_desc)
            user_desc_array_cast = user_desc_array.cast()
            char_md.p_char_user_desc = user_desc_array_cast
            char_md.char_user_desc_size = len(self.user_desc)
            char_md.char_user_desc_max_size = len(self.user_desc)
        if self.pf:
            char_md.p_char_pf = self.pf.to_c()
        if self.desc_md:
            char_md.user_desc_md = self.desc_md.to_c()
        if self.cccd_md:
            char_md.p_cccd_md = self.cccd_md.to_c()
        if self.sccd_md:
            char_md.p_sccd_md = self.sccd_md.to_c()
        return char_md


class BLEGapPhys(object):
    def __init__(self, tx_phys, rx_phys):
        self.tx_phys = tx_phys
        self.rx_phys = rx_phys

    def __str__(self):
        return str(self.__dict__)

    def to_c(self):
        gap_phys = driver.ble_gap_phys_t()
        gap_phys.tx_phys = self.tx_phys
        gap_phys.rx_phys = self.rx_phys
        return gap_phys

    @classmethod
    def from_c(cls, params):
        return cls(
            tx_phys=params.tx_phys,
            rx_phys=params.rx_phys,
        )


class BLEDescriptor(object):
    def __init__(self, uuid, handle):
        self.handle = handle
        self.uuid = uuid

    @classmethod
    def from_c(cls, gattc_desc):
        return cls(uuid=BLEUUID.from_c(gattc_desc.uuid), handle=gattc_desc.handle)

    def __str__(self):
        return "Descriptor uuid({0.uuid}) handle({0.handle})".format(self)


CharProperties = collections.namedtuple(
    "CharProperties",
    "broadcast read write_wo_resp write notify indicate auth_signed_wr",
)


class BLECharProperties(CharProperties):
    @classmethod
    def from_c(cls, char_props):
        return cls(
            broadcast=char_props.broadcast,
            read=char_props.read,
            write_wo_resp=char_props.write_wo_resp,
            write=char_props.write,
            notify=char_props.notify,
            indicate=char_props.indicate,
            auth_signed_wr=char_props.auth_signed_wr,
        )


class BLECharacteristic(object):
    def __init__(self, uuid, char_props, handle_decl, handle_value):
        self.uuid = uuid
        self.char_props = char_props
        self.handle_decl = handle_decl
        self.handle_value = handle_value
        self.end_handle = None
        self.descs = list()

    @classmethod
    def from_c(cls, gattc_char):
        return cls(
            uuid=BLEUUID.from_c(gattc_char.uuid),
            char_props=BLECharProperties.from_c(gattc_char.char_props),
            handle_decl=gattc_char.handle_decl,
            handle_value=gattc_char.handle_value,
        )

    def __repr__(self):
        return "<BLECharacteristic obj>"

    def __str__(self):
        return (
            "Characteristic uuid({0.uuid}) properties({0.char_props}) declaration handle({0.handle_decl}) "
            "value handle({0.handle_value})"
        ).format(self)


class BLEService(object):
    def __init__(self, uuid, start_handle, end_handle):
        self.uuid = uuid
        self.start_handle = start_handle
        self.end_handle = end_handle
        self.chars = list()

    @classmethod
    def from_c(cls, gattc_service):
        return cls(
            uuid=BLEUUID.from_c(gattc_service.uuid),
            start_handle=gattc_service.handle_range.start_handle,
            end_handle=gattc_service.handle_range.end_handle,
        )

    def char_add(self, char):
        char.end_handle = self.end_handle
        self.chars.append(char)
        if len(self.chars) > 1:
            self.chars[-2].end_handle = char.handle_decl - 1

    def __str__(self):
        return "Service uuid({0.uuid}) start handle({0.start_handle}) end handle({0.end_handle})".format(
            self
        )


class SerialPortDescriptor(object):
    def __init__(
        self,
        port="",
        manufacturer="",
        serial_number="",
        pnp_id="",
        location_id="",
        vendor_id="",
        product_id="",
    ):
        self.port = port
        self.manufacturer = manufacturer
        self.serial_number = serial_number
        self.pnp_id = pnp_id
        self.location_id = location_id
        self.vendor_id = vendor_id
        self.product_id = product_id

    @classmethod
    def to_string(cls, char_arr):
        s = util.char_array_to_list(char_arr, driver.SD_RPC_MAXPATHLEN)
        for i, c in enumerate(s):
            if c == "\x00":
                break
        s = s[0:i]
        s = "".join(s)
        return s

    @classmethod
    def from_c(cls, org):
        # Workaround to change from /dev/cu.X to /dev/tty.X
        # tty.X is preferred because other products use that
        # as an identifier for development kits serial ports
        port = None

        if org.port is not None and sys.platform == "darwin":
            port = org.port.replace("/cu", "/tty")
        else:
            port = org.port

        return cls(
            port=port,
            manufacturer=org.manufacturer,
            serial_number=org.serialNumber,
            pnp_id=org.pnpId,
            location_id=org.locationId,
            vendor_id=org.vendorId,
            product_id=org.productId,
        )


class BLEConfigBase(object):
    conn_cfg_tag = 1

    @abstractmethod
    def to_c(self):
        pass


class BLEConfigConnGap(BLEConfigBase):
    def __init__(self, conn_count=1, event_length=3):
        self.conn_count = conn_count
        self.event_length = event_length

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.conn_cfg.conn_cfg_tag = self.conn_cfg_tag
        ble_cfg.conn_cfg.params.gap_conn_cfg.conn_count = self.conn_count
        ble_cfg.conn_cfg.params.gap_conn_cfg.event_length = self.event_length
        return ble_cfg


class BLEConfigConnGattc(BLEConfigBase):
    def __init__(self, write_cmd_tx_queue_size=1):
        self.write_cmd_tx_queue_size = write_cmd_tx_queue_size

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.conn_cfg.conn_cfg_tag = self.conn_cfg_tag
        ble_cfg.conn_cfg.params.gattc_conn_cfg.write_cmd_tx_queue_size = (
            self.write_cmd_tx_queue_size
        )
        return ble_cfg


class BLEConfigConnGatts(BLEConfigBase):
    def __init__(self, hvn_tx_queue_size=1):
        self.hvn_tx_queue_size = hvn_tx_queue_size

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.conn_cfg.conn_cfg_tag = self.conn_cfg_tag
        ble_cfg.conn_cfg.params.gatts_conn_cfg.hvn_tx_queue_size = (
            self.hvn_tx_queue_size
        )
        return ble_cfg


class BLEConfigConnGatt(BLEConfigBase):
    def __init__(self, att_mtu=23):
        self.att_mtu = att_mtu

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.conn_cfg.conn_cfg_tag = self.conn_cfg_tag
        ble_cfg.conn_cfg.params.gatt_conn_cfg.att_mtu = self.att_mtu
        return ble_cfg


class BLEConfigConnL2cap(BLEConfigBase):
    def __init__(
        self, rx_mps=23, tx_mps=23, rx_queue_size=1, tx_queue_size=1, ch_count=0
    ):
        self.rx_mps = rx_mps
        self.tx_mps = tx_mps
        self.rx_queue_size = rx_queue_size
        self.tx_queue_size = tx_queue_size
        self.ch_count = ch_count

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.conn_cfg.conn_cfg_tag = self.conn_cfg_tag
        ble_cfg.conn_cfg.params.l2cap_conn_cfg.rx_mps = self.rx_mps
        ble_cfg.conn_cfg.params.l2cap_conn_cfg.tx_mps = self.tx_mps
        ble_cfg.conn_cfg.params.l2cap_conn_cfg.rx_queue_size = self.rx_queue_size
        ble_cfg.conn_cfg.params.l2cap_conn_cfg.tx_queue_size = self.tx_queue_size
        ble_cfg.conn_cfg.params.l2cap_conn_cfg.ch_count = self.ch_count
        return ble_cfg


class BLEConfigCommon(BLEConfigBase):
    def __init__(self, vs_uuid_count=1):
        self.vs_uuid_count = vs_uuid_count

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.common_cfg.vs_uuid_cfg.vs_uuid_count = self.vs_uuid_count
        return ble_cfg


class BLEConfigGapRoleCount(BLEConfigBase):
    def __init__(self, central_role_count=1, periph_role_count=1, central_sec_count=1):
        self.central_role_count = central_role_count
        self.periph_role_count = periph_role_count
        self.central_sec_count = central_sec_count

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.gap_cfg.role_count_cfg.periph_role_count = self.periph_role_count
        ble_cfg.gap_cfg.role_count_cfg.central_role_count = self.central_role_count
        ble_cfg.gap_cfg.role_count_cfg.central_sec_count = self.central_sec_count
        return ble_cfg


class BLEConfigGapDeviceName(BLEConfigBase):
    def __init__(self, device_name="nRF5x-py", device_name_read_only=True):
        self.device_name = device_name
        self.device_name_read_only = device_name_read_only
        self.__device_name = None

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        if self.device_name_read_only:
            ble_cfg.gap_cfg.device_name_cfg.write_perm.sm = 0
            ble_cfg.gap_cfg.device_name_cfg.write_perm.lv = 0
        else:
            ble_cfg.gap_cfg.device_name_cfg.write_perm.sm = 1
            ble_cfg.gap_cfg.device_name_cfg.write_perm.lv = 1

        ble_cfg.gap_cfg.device_name_cfg.vloc = 2
        self.__device_name = util.list_to_uint8_array(
            [ord(x) for x in self.device_name]
        )
        ble_cfg.gap_cfg.device_name_cfg.p_value = self.__device_name.cast()
        ble_cfg.gap_cfg.device_name_cfg.current_len = len(self.device_name)
        ble_cfg.gap_cfg.device_name_cfg.max_len = len(self.device_name)
        return ble_cfg


class BLEConfigGatts(BLEConfigBase):
    def __init__(self, service_changed=1, attr_tab_size=1):
        self.service_changed = service_changed
        self.attr_tab_size = attr_tab_size

    def to_c(self):
        ble_cfg = driver.ble_cfg_t()
        ble_cfg.gatts_cfg.service_changed.service_changed = self.service_changed
        ble_cfg.gatts_cfg.attr_tab_size.attr_tab_size = self.attr_tab_size
        return ble_cfg


class BLEGapDataLengthParams(object):
    def __init__(
        self,
        max_tx_octets=251,
        max_rx_octets=251,
        max_tx_time_us=0,  # BLE_GAP_DATA_LENGTH_AUTO
        max_rx_time_us=0,
    ):  # BLE_GAP_DATA_LENGTH_AUTO
        self.max_tx_octets = max_tx_octets
        self.max_rx_octets = max_rx_octets
        self.max_tx_time_us = max_tx_time_us
        self.max_rx_time_us = max_rx_time_us

    @classmethod
    def from_c(cls, params):
        return cls(
            max_tx_octets=params.max_tx_octets,
            max_rx_octets=params.max_rx_octets,
            max_tx_time_us=params.max_tx_time_us,
            max_rx_time_us=params.max_rx_time_us,
        )

    def to_c(self):
        dlp = driver.ble_gap_data_length_params_t()
        dlp.max_tx_octets = self.max_tx_octets
        dlp.max_rx_octets = self.max_rx_octets
        dlp.max_tx_time_us = self.max_tx_time_us
        dlp.max_rx_time_us = self.max_rx_time_us
        return dlp


class BLEGapDataLengthLimitation(object):
    def __init__(
        self,
        tx_payload_limited_octets=0,
        rx_payload_limited_octets=0,
        tx_rx_time_limited_us=0,
    ):
        self.tx_payload_limited_octets = tx_payload_limited_octets
        self.rx_payload_limited_octets = rx_payload_limited_octets
        self.tx_rx_time_limited_us = tx_rx_time_limited_us

    def to_c(self):
        dll = driver.ble_gap_data_length_limitation_t()
        dll.tx_payload_limited_octets = self.tx_payload_limited_octets
        dll.rx_payload_limited_octets = self.rx_payload_limited_octets
        dll.tx_rx_time_limited_us = self.tx_rx_time_limited_us
        return dll

    @classmethod
    def from_c(cls, data_length_limitation):
        return cls(
            tx_payload_limited_octets=data_length_limitation.tx_payload_limited_octets,
            rx_payload_limited_octets=data_length_limitation.rx_payload_limited_octets,
            tx_rx_time_limited_us=data_length_limitation.tx_rx_time_limited_us,
        )


class RpcAppStatus(Enum):
    pktSendMaxRetriesReached = driver.PKT_SEND_MAX_RETRIES_REACHED
    pktUnexpected = driver.PKT_UNEXPECTED
    pktEncodeError = driver.PKT_ENCODE_ERROR
    pktDecodeError = driver.PKT_DECODE_ERROR
    pktSendError = driver.PKT_SEND_ERROR
    ioResourcesUnavailable = driver.IO_RESOURCES_UNAVAILABLE
    resetPerformed = driver.RESET_PERFORMED
    connectionActive = driver.CONNECTION_ACTIVE


class RpcLogSeverity(Enum):
    trace = driver.SD_RPC_LOG_TRACE
    debug = driver.SD_RPC_LOG_DEBUG
    info = driver.SD_RPC_LOG_INFO
    warning = driver.SD_RPC_LOG_WARNING
    error = driver.SD_RPC_LOG_ERROR
    fatal = driver.SD_RPC_LOG_FATAL


class BLEDriver(object):
    observer_lock = Lock()
    api_lock = Lock()

    def __init__(
        self,
        serial_port,  # type: str
        baud_rate=1000000,  # type: int
        auto_flash=False,  # type: bool
        retransmission_interval=300,  # type: int
        response_timeout=1500,  # type: int
        log_severity_level="info",  # type: str
    ):
        super(BLEDriver, self).__init__()
        self.observers = list()  # type: List[BLEDriverObserver]

        if auto_flash:
            try:
                flasher = Flasher(serial_port=serial_port)
            except Exception:
                logger.error("Unable to find serial port")
                raise

            if not flasher.fw_check():
                logger.info("Flashing '{}' board with '{}' firmware"
                            .format(serial_port, config.conn_ic_hex_get()))
                flasher.fw_flash()

            flasher.reset()
            time.sleep(1)

        phy_layer = driver.sd_rpc_physical_layer_create_uart(
            serial_port,
            baud_rate,
            driver.SD_RPC_FLOW_CONTROL_NONE,
            driver.SD_RPC_PARITY_NONE,
        )
        link_layer = driver.sd_rpc_data_link_layer_create_bt_three_wire(
            phy_layer, retransmission_interval
        )
        transport_layer = driver.sd_rpc_transport_layer_create(
            link_layer, response_timeout
        )
        self.rpc_adapter = driver.sd_rpc_adapter_create(transport_layer)
        log_severity_level_enum = getattr(
            RpcLogSeverity, log_severity_level.lower(), RpcLogSeverity.info
        )
        self.rpc_log_severity_filter(log_severity_level_enum)
        self._keyset = self.init_keyset()

        self.log_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.ble_event_queue = queue.Queue()

    def init_keyset(self):
        keyset = driver.ble_gap_sec_keyset_t()

        keyset.keys_own.p_enc_key = driver.ble_gap_enc_key_t()
        keyset.keys_own.p_id_key = driver.ble_gap_id_key_t()
        keyset.keys_own.p_sign_key = driver.ble_gap_sign_info_t()
        keyset.keys_own.p_pk = driver.ble_gap_lesc_p256_pk_t()

        keyset.keys_peer.p_enc_key = driver.ble_gap_enc_key_t()
        keyset.keys_peer.p_id_key = driver.ble_gap_id_key_t()
        keyset.keys_peer.p_sign_key = driver.ble_gap_sign_info_t()
        keyset.keys_peer.p_pk = driver.ble_gap_lesc_p256_pk_t()

        return keyset

    def generate_lesc_keyset(self, private_key=None):
        def _int_to_list(input_integer):
            output_list = []
            input_hex_string = "{:X}".format(input_integer)

            # Add zeros to start key if they are stripped.
            while len(input_hex_string) < 64:
                input_hex_string = "0" + input_hex_string

            for i in range(1, len(input_hex_string), 2):
                output_list.append(int((input_hex_string[i - 1] + input_hex_string[i]), 16))

            return output_list

        self._lesc_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        if not private_key:
            private_key = self._lesc_private_key
        lesc_own_public_key = private_key.public_key()
        lesc_own_public_key_numbers = lesc_own_public_key.public_numbers()
        lesc_own_public_key = private_key.public_key()
        x = lesc_own_public_key_numbers.x
        y = lesc_own_public_key_numbers.y

        logger.debug("ECDH key: Before: x: {:X}".format(x))
        logger.debug("ECDH key: Before: y: {:X}".format(y))

        x_list = _int_to_list(x)[::-1]
        y_list = _int_to_list(y)[::-1]

        logger.debug("ECDH key: After: x: {}".format(" ".join(["0x{:02X}".format(i) for i in x_list])))
        logger.debug("ECDH key: After: y: {}".format(" ".join(["0x{:02X}".format(i) for i in y_list])))
        lesc_own_public_key_list = x_list + y_list

        # Put own lesc public key into keyset.
        lesc_pk_own = BLEGapLescP256Pk(lesc_own_public_key_list)
        logger.debug("lesc_pk_own {}".format(lesc_pk_own))
        self._keyset.keys_own.p_pk = lesc_pk_own.to_c()

        return self._keyset

    def generate_lesc_dhkey(self, peer_public_key):
        def _change_endianness(input_string):
            output = ""
            for i in range(len(input_string) - 1, 0, -2):
                output += input_string[i - 1]
                output += input_string[i]
            return output
        lesc_pk_peer = peer_public_key
        # Translate incoming peer public key to x an y components as integers.
        peer_public_key_list = lesc_pk_peer.pk
        peer_public_key_x = int(_change_endianness("".join(["{:02X}".format(i) for i in peer_public_key_list[:32]])), 16)
        peer_public_key_y = int(_change_endianness("".join(["{:02X}".format(i) for i in peer_public_key_list[32:]])), 16)

        logger.debug("Peer public DH key, big endian, x: 0x{:X}, y: 0x{:X}".format(peer_public_key_x, peer_public_key_y))

        # Generate a _EllipticCurvePublicKey object of the received peer public key.
        lesc_peer_public_key_obj = ec.EllipticCurvePublicNumbers(peer_public_key_x,
                                                                 peer_public_key_y,
                                                                 ec.SECP256R1())
        lesc_peer_public_key_obj2 = lesc_peer_public_key_obj.public_key(default_backend())

        # Calculate shared secret based on own private key and peer public key.
        shared_key_list = self._lesc_private_key.exchange(ec.ECDH(), lesc_peer_public_key_obj2)
        shared_key_list = list(shared_key_list)
        shared_key_list = shared_key_list[::-1]
        logger.debug("shared_key_list = {}".format(shared_key_list))

        key_list_string = " ".join(["0x{:02X}".format(i) for i in shared_key_list])
        logger.debug("Shared secret list, little endian: {} \n".format(key_list_string))
        logger.debug("len(shared_key_list) = {}".format(len(shared_key_list)))
        # Reply to Softdevice with shared key
        lesc_dhkey = BLEGapDHKey(shared_key_list).to_c()
        return lesc_dhkey

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def rpc_log_severity_filter(self, severity):
        # type: (RpcLogSeverity) -> ()
        return driver.sd_rpc_log_handler_severity_filter_set(
            self.rpc_adapter, severity.value
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_cfg_set(self, cfg_id, cfg):
        app_ram_base = 0
        assert isinstance(cfg, BLEConfigBase)
        assert isinstance(cfg_id, BLEConfig)
        return driver.sd_ble_cfg_set(
            self.rpc_adapter, cfg_id.value, cfg.to_c(), app_ram_base
        )

    @wrapt.synchronized(api_lock)
    @classmethod
    def enum_serial_ports(cls):
        MAX_SERIAL_PORTS = 64
        c_descs = [driver.sd_rpc_serial_port_desc_t() for _ in range(MAX_SERIAL_PORTS)]
        c_desc_arr = util.list_to_serial_port_desc_array(c_descs)

        arr_len = driver.new_uint32()
        driver.uint32_assign(arr_len, MAX_SERIAL_PORTS)

        err_code = driver.sd_rpc_serial_port_enum(c_desc_arr, arr_len)
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException(
                "Failed to {}. Error code: {}".format(
                    BLEDriver.enum_serial_ports.__name__, err_code
                )
            )

        dlen = driver.uint32_value(arr_len)

        descs = util.serial_port_desc_array_to_list(c_desc_arr, dlen)
        return list(map(SerialPortDescriptor.from_c, descs))

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def open(self):
        self.run_workers = True

        self.log_worker = Thread(
            target=self.log_message_handler_thread, name="LogThread"
        )
        self.log_worker.daemon = True
        self.log_worker.start()

        self.status_worker = Thread(
            target=self.status_handler_thread, name="StatusThread"
        )
        self.status_worker.daemon = True
        self.status_worker.start()

        self.ble_event_worker = Thread(
            target=self.ble_event_handler_thread, name="EventThread"
        )
        self.ble_event_worker.daemon = True
        self.ble_event_worker.start()

        return driver.sd_rpc_open(
            self.rpc_adapter,
            self.status_handler,
            self.ble_event_handler,
            self.log_message_handler,
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def close(self):
        result = driver.sd_rpc_close(self.rpc_adapter)
        logger.debug("close result %s", result)

        # Cleanup workers
        if self.run_workers:
            self.run_workers = False

            logger.debug("Stopping workers")

            self.log_worker.join()

            # Empty log_queue
            try:
                while True:
                    self.log_queue.get_nowait()
            except queue.Empty:
                pass

            self.status_worker.join()

            # Empty status_queue
            try:
                while True:
                    self.status_queue.get_nowait()
            except queue.Empty:
                pass

            self.ble_event_worker.join()

            # Empty ble_event_queue
            try:
                while True:
                    self.ble_event_queue.get_nowait()
            except queue.Empty:
                pass

            logger.debug("Workers stopped")

        return result

    @wrapt.synchronized(observer_lock)
    def observer_register(self, observer):
        self.observers.append(observer)

    @wrapt.synchronized(observer_lock)
    def observer_unregister(self, observer):
        self.observers.remove(observer)

    @staticmethod
    def adv_params_setup():
        return BLEGapAdvParams(interval_ms=40, timeout_s=180)

    @staticmethod
    def scan_params_setup():
        return BLEGapScanParams(interval_ms=200, window_ms=150, timeout_s=10)

    @staticmethod
    def conn_params_setup():
        return BLEGapConnParams(
            min_conn_interval_ms=15,
            max_conn_interval_ms=30,
            conn_sup_timeout_ms=4000,
            slave_latency=0,
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_enable(self, ble_enable_params=None):
        app_ram_base = driver.new_uint32()
        if nrf_sd_ble_api_ver == 2:
            assert isinstance(ble_enable_params, BLEEnableParams)
            err_code = driver.sd_ble_enable(
                self.rpc_adapter, ble_enable_params.to_c(), app_ram_base
            )
        elif nrf_sd_ble_api_ver == 5:
            assert (
                ble_enable_params is None
            ), "ble_enable_params not used in s132 v5 API"
            driver.uint32_assign(app_ram_base, 0)
            err_code = driver.sd_ble_enable(self.rpc_adapter, app_ram_base)
        return err_code

    @wrapt.synchronized(api_lock)
    def ble_version_get(self):
        version = driver.ble_version_t()
        err_code = driver.sd_ble_version_get(self.rpc_adapter, version)

        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException(
                "Failed to get ble_version. Error code: {}".format(err_code)
            )

        return BLEVersion.from_c(version)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_addr_set(self, gap_addr):
        assert isinstance(gap_addr, BLEGapAddr), "Invalid argument type"
        if gap_addr:
            gap_addr = gap_addr.to_c()
        if nrf_sd_ble_api_ver == 2:
            return driver.sd_ble_gap_address_set(self.rpc_adapter, 0, gap_addr)
        elif nrf_sd_ble_api_ver == 5:
            return driver.sd_ble_gap_addr_set(self.rpc_adapter, gap_addr)

    @wrapt.synchronized(api_lock)
    def ble_gap_addr_get(self):
        address = BLEGapAddr(BLEGapAddr.Types.public, [0] * 6)
        addr = address.to_c()
        if nrf_sd_ble_api_ver >= 3:
            err_code = driver.sd_ble_gap_addr_get(self.rpc_adapter, addr)
        else:
            err_code = driver.sd_ble_gap_address_get(self.rpc_adapter, addr)
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException(
                "Failed to get ble_gap_addr. Error code: {}".format(err_code)
            )
        return BLEGapAddr.from_c(addr)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_privacy_set(self, privacy_params):
        assert isinstance(privacy_params, BLEGapPrivacyParams), "Invalid argument type"
        privacy_params = privacy_params.to_c()
        return driver.sd_ble_gap_privacy_set(self.rpc_adapter, privacy_params)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_adv_start(self, adv_params=None, tag=0):
        if not adv_params:
            adv_params = self.adv_params_setup()
        assert isinstance(adv_params, BLEGapAdvParams), "Invalid argument type"
        if nrf_sd_ble_api_ver == 5:
            return driver.sd_ble_gap_adv_start(self.rpc_adapter, adv_params.to_c(), tag)
        else:
            return driver.sd_ble_gap_adv_start(self.rpc_adapter, adv_params.to_c())

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_conn_param_update(self, conn_handle, conn_params):
        assert isinstance(
            conn_params, (BLEGapConnParams, type(None))
        ), "Invalid argument type"
        if not conn_params:
            conn_params = self.conn_params_setup()
        return driver.sd_ble_gap_conn_param_update(
            self.rpc_adapter, conn_handle, conn_params.to_c()
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_adv_stop(self):
        return driver.sd_ble_gap_adv_stop(self.rpc_adapter)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_scan_start(self, scan_params=None):
        if not scan_params:
            scan_params = self.scan_params_setup()
        assert isinstance(scan_params, BLEGapScanParams), "Invalid argument type"
        return driver.sd_ble_gap_scan_start(self.rpc_adapter, scan_params.to_c())

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_scan_stop(self):
        return driver.sd_ble_gap_scan_stop(self.rpc_adapter)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_connect(self, address, scan_params=None, conn_params=None, tag=0):
        assert isinstance(address, BLEGapAddr), "Invalid argument type"

        if not scan_params:
            scan_params = self.scan_params_setup()
        assert isinstance(scan_params, BLEGapScanParams), "Invalid argument type"

        if not conn_params:
            conn_params = self.conn_params_setup()
        assert isinstance(conn_params, BLEGapConnParams), "Invalid argument type"

        if nrf_sd_ble_api_ver == 2:
            return driver.sd_ble_gap_connect(
                self.rpc_adapter, address.to_c(), scan_params.to_c(), conn_params.to_c()
            )
        elif nrf_sd_ble_api_ver == 5:
            return driver.sd_ble_gap_connect(
                self.rpc_adapter,
                address.to_c(),
                scan_params.to_c(),
                conn_params.to_c(),
                tag,
            )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_disconnect(
        self, conn_handle, hci_status_code=BLEHci.remote_user_terminated_connection
    ):
        assert isinstance(hci_status_code, BLEHci), "Invalid argument type"
        return driver.sd_ble_gap_disconnect(
            self.rpc_adapter, conn_handle, hci_status_code.value
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_adv_data_set(self, adv_data=BLEAdvData(), scan_data=BLEAdvData()):
        assert isinstance(adv_data, BLEAdvData), "Invalid argument type"
        assert isinstance(scan_data, BLEAdvData), "Invalid argument type"
        (adv_data_len, p_adv_data) = adv_data.to_c()
        (scan_data_len, p_scan_data) = scan_data.to_c()

        return driver.sd_ble_gap_adv_data_set(
            self.rpc_adapter, p_adv_data, adv_data_len, p_scan_data, scan_data_len
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_authenticate(self, conn_handle, sec_params):
        assert isinstance(
            sec_params, (BLEGapSecParams, type(None))
        ), "Invalid argument type"
        return driver.sd_ble_gap_authenticate(
            self.rpc_adapter, conn_handle, sec_params.to_c() if sec_params else None
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_sec_params_reply(self, conn_handle, sec_status, sec_params, keyset=None):
        assert isinstance(sec_status, BLEGapSecStatus), "Invalid argument type"
        assert isinstance(sec_params, (BLEGapSecParams, NoneType)), "Invalid argument type"

        if keyset is not None:
            self._keyset = keyset

        return driver.sd_ble_gap_sec_params_reply(
            self.rpc_adapter,
            conn_handle,
            sec_status.value,
            sec_params.to_c() if sec_params else None,
            self._keyset
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_lesc_dhkey_reply(self, conn_handle, p_dhkey):
        return driver.sd_ble_gap_lesc_dhkey_reply(
            self.rpc_adapter,
            conn_handle,
            p_dhkey
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_sec_info_reply(self, conn_handle, enc_info, id_info, sign_info):
        return driver.sd_ble_gap_sec_info_reply(
            self.rpc_adapter, conn_handle, enc_info, id_info, sign_info
        )

    @wrapt.synchronized(api_lock)
    def ble_gap_conn_sec_get(self, conn_handle):
        conn_sec = driver.ble_gap_conn_sec_t()
        conn_sec.sec_mode = driver.ble_gap_conn_sec_mode_t()
        err_code = driver.sd_ble_gap_conn_sec_get(
            self.rpc_adapter, conn_handle, conn_sec
        )
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException(
                "Failed to get ble_gap_conn_sec. Error code: {}".format(err_code)
            )
        return conn_sec

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_encrypt(self, conn_handle, master_id, enc_info, lesc):
        if not master_id or not enc_info:
            keyset = BLEGapSecKeyset.from_c(self._keyset)
            if lesc:
                master_id = keyset.keys_own.p_enc_key.master_id
                enc_info = keyset.keys_own.p_enc_key.enc_info
            else:
                master_id = keyset.keys_peer.p_enc_key.master_id
                enc_info = keyset.keys_peer.p_enc_key.enc_info
        assert isinstance(master_id, BLEGapMasterId), 'Invalid argument type'
        assert isinstance(enc_info, BLEGapEncInfo), 'Invalid argument type'
        logger.info("ble_gap_encrypt. \n   master_id: {}\n   enc_info: {}".format(master_id, enc_info))
        return driver.sd_ble_gap_encrypt(
            self.rpc_adapter, conn_handle, master_id.to_c(), enc_info.to_c()
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_data_length_update(
        self, conn_handle, data_length_params, data_length_limitation
    ):
        assert nrf_sd_ble_api_ver >= 5, 'Data Length Update requires SD API v5 or higher'
        assert isinstance(data_length_params, (BLEGapDataLengthParams, type(None)))
        assert isinstance(
            data_length_limitation, (BLEGapDataLengthLimitation, type(None))
        )
        dll = driver.new_ble_gap_data_length_limitation()
        err_code = driver.sd_ble_gap_data_length_update(
            self.rpc_adapter,
            conn_handle,
            data_length_params.to_c() if data_length_params else None,
            dll,
        )
        if err_code != driver.NRF_SUCCESS:
            # TODO: figure out what the purpose is with this code
            value = driver.ble_gap_data_length_limitation_value(dll)
            data_length_limitation = BLEGapDataLengthLimitation.from_c(value)
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_rssi_start(self, conn_handle, threshold_dbm, skip_count):
        return driver.sd_ble_gap_rssi_start(
            self.rpc_adapter, conn_handle, threshold_dbm, skip_count
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_rssi_stop(self, conn_handle):
        return driver.sd_ble_gap_rssi_stop(self.rpc_adapter, conn_handle)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gap_phy_update(self, conn_handle, gap_phys):
        assert nrf_sd_ble_api_ver >= 5, 'PHY Update requires SD API v5 or higher'
        assert isinstance(gap_phys, BLEGapPhys)
        gap_phys_c = gap_phys.to_c()
        err_code = driver.sd_ble_gap_phy_update(self.rpc_adapter, conn_handle, gap_phys_c)
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException(
                "Failed to update phy. Error code: {}".format(err_code)
            )
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_vs_uuid_add(self, uuid_base):
        assert isinstance(uuid_base, BLEUUIDBase), "Invalid argument type"
        uuid_type = driver.new_uint8()

        err_code = driver.sd_ble_uuid_vs_add(
            self.rpc_adapter, uuid_base.to_c(), uuid_type
        )
        if err_code == driver.NRF_SUCCESS:
            uuid_base.type = driver.uint8_value(uuid_type)
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_uuid_decode(self, uuid_list, uuid):
        uuid_len = len(uuid_list)
        assert isinstance(uuid_list, list), "Invalid argument type"
        assert ((uuid_len == 2) or (uuid_len == 16)), "Invalid uuid length"
        assert isinstance(uuid, BLEUUID)

        lsb_list = uuid_list[::-1]
        uuid_le_array = util.list_to_uint8_array(lsb_list)
        uuid_le_array_cast = uuid_le_array.cast()
        uuid.base.type = 0xFF  # Placeholder value

        uuid_c = uuid.to_c()

        err_code = driver.sd_ble_uuid_decode(self.rpc_adapter, uuid_len, uuid_le_array_cast,
                                             uuid_c)
        if err_code == driver.NRF_SUCCESS:
            uuid_from_c = BLEUUID.from_c(uuid_c)
            uuid.base.type = uuid_from_c.base.type
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_write(self, conn_handle, write_params):
        assert isinstance(write_params, BLEGattcWriteParams), "Invalid argument type"
        return driver.sd_ble_gattc_write(
            self.rpc_adapter, conn_handle, write_params.to_c()
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_read(self, conn_handle, handle, offset):
        return driver.sd_ble_gattc_read(self.rpc_adapter, conn_handle, handle, offset)

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_prim_srvc_disc(self, conn_handle, srvc_uuid, start_handle):
        assert isinstance(srvc_uuid, (BLEUUID, type(None))), "Invalid argument type"
        return driver.sd_ble_gattc_primary_services_discover(
            self.rpc_adapter,
            conn_handle,
            start_handle,
            srvc_uuid.to_c() if srvc_uuid else None,
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_char_disc(self, conn_handle, start_handle, end_handle):
        handle_range = driver.ble_gattc_handle_range_t()
        handle_range.start_handle = start_handle
        handle_range.end_handle = end_handle
        return driver.sd_ble_gattc_characteristics_discover(
            self.rpc_adapter, conn_handle, handle_range
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_desc_disc(self, conn_handle, start_handle, end_handle):
        handle_range = driver.ble_gattc_handle_range_t()
        handle_range.start_handle = start_handle
        handle_range.end_handle = end_handle
        return driver.sd_ble_gattc_descriptors_discover(
            self.rpc_adapter, conn_handle, handle_range
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_exchange_mtu_req(self, conn_handle, mtu):
        return driver.sd_ble_gattc_exchange_mtu_request(
            self.rpc_adapter, conn_handle, mtu
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gattc_hv_confirm(self, conn_handle, attr_handle):
        return driver.sd_ble_gattc_hv_confirm(
            self.rpc_adapter, conn_handle, attr_handle
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gatts_service_add(self, service_type, uuid, service_handle):
        assert isinstance(service_handle, BLEGattHandle)
        assert isinstance(uuid, BLEUUID)
        handle = driver.new_uint16()
        uuid_c = uuid.to_c()
        err_code = driver.sd_ble_gatts_service_add(
            self.rpc_adapter, service_type, uuid_c, handle
        )
        if err_code == driver.NRF_SUCCESS:
            service_handle.handle = driver.uint16_value(handle)
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gatts_characteristic_add(
        self, service_handle, char_md, attr_char_value, char_handle
    ):
        assert isinstance(char_handle, BLEGattsCharHandles), "Invalid argument type"
        handles = driver.ble_gatts_char_handles_t()
        char_md = char_md.to_c()
        attr_char_value = attr_char_value.to_c()
        err_code = driver.sd_ble_gatts_characteristic_add(
            self.rpc_adapter, service_handle, char_md, attr_char_value, handles
        )
        if err_code == driver.NRF_SUCCESS:
            char_handle.value_handle = handles.value_handle
            char_handle.user_desc_handle = handles.user_desc_handle
            char_handle.cccd_handle = handles.cccd_handle
            char_handle.sccd_handle = handles.sccd_handle
        return err_code

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gatts_exchange_mtu_reply(self, conn_handle, mtu):
        return driver.sd_ble_gatts_exchange_mtu_reply(
            self.rpc_adapter, conn_handle, mtu
        )

    @NordicSemiErrorCheck
    @wrapt.synchronized(api_lock)
    def ble_gatts_hvx(self, conn_handle, hvx_params):
        assert isinstance(hvx_params, BLEGattsHVXParams), "Invalid argument type"
        hvx_params = hvx_params.to_c()
        return driver.sd_ble_gatts_hvx(self.rpc_adapter, conn_handle, hvx_params)

    def ble_gatts_sys_attr_set(self, conn_handle, sys_attr_data, length, flags):
        return driver.sd_ble_gatts_sys_attr_set(self.rpc_adapter, conn_handle,
                                                sys_attr_data, length, flags)

    # IMPORTANT: Python annotations on callbacks make the reference count
    # IMPORTANT: for the object become zero in the binding. This makes the
    # IMPORTANT: interpreter crash since it tries to garbage collect
    # IMPORTANT: the object from the binding.
    def status_handler(self, adapter, status_code, status_message):
        if self.rpc_adapter.internal == adapter.internal:
            if self.status_queue:
                self.status_queue.put([adapter, status_code, status_message])
        else:
            logger.error("status_handler")

    @wrapt.synchronized(observer_lock)
    def status_handler_sync(self, adapter, status_code, status_message):
        statusEnum = RpcAppStatus(status_code)

        for obs in self.observers:
            obs.on_rpc_status(adapter, statusEnum, status_message)

    def status_handler_thread(self):
        while self.run_workers:
            try:
                item = self.status_queue.get(True, WORKER_QUEUE_WAIT_TIME)
                self.status_handler_sync(*item)
            except queue.Empty:
                pass
            except Exception as ex:
                logger.exception("Exception in status handler: {}".format(ex))

    # IMPORTANT: Python annotations on callbacks make the reference count
    # IMPORTANT: for the object become zero in the binding. This makes the
    # IMPORTANT: interpreter crash since it tries to garbage collect
    # IMPORTANT: the object from the binding.
    def log_message_handler(self, adapter, severity, log_message):
        if self.rpc_adapter.internal == adapter.internal:
            self.log_queue.put([adapter, severity, log_message])
        else:
            logger.error("log_message_handler")

    @wrapt.synchronized(observer_lock)
    def log_message_handler_sync(self, adapter, severity, log_message):
        severityEnum = RpcLogSeverity(severity)
        logLevel = None  # type: int

        if severityEnum in (RpcLogSeverity.trace, RpcLogSeverity.debug):
            logLevel = logging.DEBUG
        elif severityEnum == RpcLogSeverity.info:
            logLevel = logging.INFO
        elif severityEnum == RpcLogSeverity.warning:
            logLevel = logging.WARNING
        elif severityEnum == RpcLogSeverity.error:
            logLevel = logging.ERROR
        elif severityEnum == RpcLogSeverity.fatal:
            logLevel = logging.FATAL

        for obs in self.observers:
            obs.on_rpc_log_entry(adapter, logLevel, log_message)

    def log_message_handler_thread(self):
        while self.run_workers:
            try:
                item = self.log_queue.get(True, WORKER_QUEUE_WAIT_TIME)
                self.log_message_handler_sync(*item)
            except queue.Empty:
                pass
            except Exception as ex:
                logger.exception("Exception in log handler: {}".format(ex))

    def ble_event_handler_thread(self):
        while self.run_workers:
            try:
                item = self.ble_event_queue.get(True, WORKER_QUEUE_WAIT_TIME)
                self.ble_event_handler_sync(*item)
            except queue.Empty:
                pass
            except Exception as ex:
                logger.exception("Exception in event handler: {}".format(ex))

    def ble_event_handler(self, adapter, ble_event):
        if self.rpc_adapter.internal == adapter.internal:
            self.ble_event_queue.put([adapter, ble_event])
        else:
            logger.error(
                "ble_event_handler, event for adapter %d, current adapter is %d",
                adapter.internal,
                self.rpc_adapter.internal,
            )

    @wrapt.synchronized(observer_lock)
    def ble_event_handler_sync(self, _adapter, ble_event):

        try:
            evt_id = BLEEvtID(ble_event.header.evt_id)
        except Exception:
            logger.error(
                "Invalid received BLE event id: 0x{:02X}".format(
                    ble_event.header.evt_id
                )
            )
            return
        try:

            if evt_id == BLEEvtID.gap_evt_connected:
                connected_evt = ble_event.evt.gap_evt.params.connected

                for obs in self.observers:
                    obs.on_gap_evt_connected(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        peer_addr=BLEGapAddr.from_c(connected_evt.peer_addr),
                        role=BLEGapRoles(connected_evt.role),
                        conn_params=BLEGapConnParams.from_c(connected_evt.conn_params),
                    )

            elif evt_id == BLEEvtID.gap_evt_disconnected:
                disconnected_evt = ble_event.evt.gap_evt.params.disconnected
                try:
                    reason = BLEHci(disconnected_evt.reason)
                except ValueError:
                    reason = disconnected_evt.reason
                for obs in self.observers:
                    obs.on_gap_evt_disconnected(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        reason=reason,
                    )

            elif evt_id == BLEEvtID.gap_evt_sec_params_request:
                sec_params_request_evt = ble_event.evt.gap_evt.params.sec_params_request

                for obs in self.observers:
                    obs.on_gap_evt_sec_params_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        peer_params=BLEGapSecParams.from_c(
                            sec_params_request_evt.peer_params
                        ),
                    )

            elif evt_id == BLEEvtID.gap_evt_sec_info_request:
                seq_info_evt = ble_event.evt.gap_evt.params.sec_info_request

                for obs in self.observers:
                    obs.on_gap_evt_sec_info_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        peer_addr=seq_info_evt.peer_addr,
                        master_id=seq_info_evt.master_id,
                        enc_info=seq_info_evt.enc_info,
                        id_info=seq_info_evt.id_info,
                        sign_info=seq_info_evt.sign_info,
                    )

            elif evt_id == BLEEvtID.gap_evt_sec_request:
                seq_req_evt = ble_event.evt.gap_evt.params.sec_request

                for obs in self.observers:
                    obs.on_gap_evt_sec_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        bond=seq_req_evt.bond,
                        mitm=seq_req_evt.mitm,
                        lesc=seq_req_evt.lesc,
                        keypress=seq_req_evt.keypress,
                    )
            elif evt_id == BLEEvtID.gap_evt_passkey_display:
                for obs in self.observers:
                    passkey = BLEGapPasskeyDisplay.from_c(ble_event.evt.gap_evt.params.passkey_display)

                    obs.on_gap_evt_passkey_display(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        passkey=passkey.passkey
                    )
            elif evt_id == BLEEvtID.gap_evt_timeout:
                timeout_evt = ble_event.evt.gap_evt.params.timeout
                try:
                    src = BLEGapTimeoutSrc(timeout_evt.src)
                except ValueError:
                    src = timeout_evt.src
                for obs in self.observers:
                    obs.on_gap_evt_timeout(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        src=src,
                    )

            elif evt_id == BLEEvtID.gap_evt_adv_report:
                adv_report_evt = ble_event.evt.gap_evt.params.adv_report
                adv_type = None
                if not adv_report_evt.scan_rsp:
                    adv_type = BLEGapAdvType(adv_report_evt.type)

                for obs in self.observers:
                    obs.on_gap_evt_adv_report(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gap_evt.conn_handle,
                        peer_addr=BLEGapAddr.from_c(adv_report_evt.peer_addr),
                        rssi=adv_report_evt.rssi,
                        adv_type=adv_type,
                        adv_data=BLEAdvData.from_c(adv_report_evt),
                    )

            elif evt_id == BLEEvtID.gap_evt_conn_param_update_request:
                conn_params = (
                    ble_event.evt.gap_evt.params.conn_param_update_request.conn_params
                )

                for obs in self.observers:
                    obs.on_gap_evt_conn_param_update_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        conn_params=BLEGapConnParams.from_c(conn_params),
                    )

            elif evt_id == BLEEvtID.gap_evt_conn_param_update:
                conn_params = ble_event.evt.gap_evt.params.conn_param_update.conn_params
                for obs in self.observers:
                    obs.on_gap_evt_conn_param_update(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        conn_params=BLEGapConnParams.from_c(conn_params),
                    )

            elif evt_id == BLEEvtID.gap_evt_lesc_dhkey_request:
                lesc_dhkey_request_evt = ble_event.evt.gap_evt.params.lesc_dhkey_request
                self._keyset.keys_peer.p_pk = lesc_dhkey_request_evt.p_pk_peer

                for obs in self.observers:
                    obs.on_gap_evt_lesc_dhkey_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        peer_public_key=BLEGapLescP256Pk.from_c(lesc_dhkey_request_evt.p_pk_peer),
                        oobd_req=lesc_dhkey_request_evt.oobd_req
                    )

            elif evt_id == BLEEvtID.gap_evt_auth_status:
                auth_status_evt = ble_event.evt.gap_evt.params.auth_status

                for obs in self.observers:
                    obs.on_gap_evt_auth_status(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        error_src=auth_status_evt.error_src,
                        bonded=auth_status_evt.bonded,
                        sm1_levels=auth_status_evt.sm1_levels,
                        sm2_levels=auth_status_evt.sm2_levels,
                        kdist_own=BLEGapSecKDist.from_c(auth_status_evt.kdist_own),
                        kdist_peer=BLEGapSecKDist.from_c(auth_status_evt.kdist_peer),
                        auth_status=BLEGapSecStatus(auth_status_evt.auth_status),
                    )

            elif evt_id == BLEEvtID.gap_evt_auth_key_request:
                auth_key_request_evt = ble_event.evt.gap_evt.params.auth_key_request

                for obs in self.observers:
                    obs.on_gap_evt_auth_key_request(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        key_type=auth_key_request_evt.key_type,
                    )

            elif evt_id == BLEEvtID.gap_evt_conn_sec_update:
                conn_sec_update_evt = ble_event.evt.gap_evt.params.conn_sec_update

                for obs in self.observers:
                    obs.on_gap_evt_conn_sec_update(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        conn_sec=BLEGapConnSec.from_c(conn_sec_update_evt.conn_sec),
                    )
            elif evt_id == BLEEvtID.gap_evt_rssi_changed:
                rssi_changed_evt = ble_event.evt.gap_evt.params.rssi_changed

                for obs in self.observers:
                    obs.on_gap_evt_rssi_changed(
                        ble_driver=self,
                        conn_handle=ble_event.evt.common_evt.conn_handle,
                        rssi=rssi_changed_evt.rssi,
                    )

            elif evt_id == BLEEvtID.gattc_evt_write_rsp:
                write_rsp_evt = ble_event.evt.gattc_evt.params.write_rsp

                for obs in self.observers:
                    obs.on_gattc_evt_write_rsp(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        error_handle=ble_event.evt.gattc_evt.error_handle,
                        attr_handle=write_rsp_evt.handle,
                        write_op=BLEGattWriteOperation(write_rsp_evt.write_op),
                        offset=write_rsp_evt.offset,
                        data=util.uint8_array_to_list(
                            write_rsp_evt.data, write_rsp_evt.len
                        ),
                    )

            elif evt_id == BLEEvtID.gattc_evt_read_rsp:
                read_rsp_evt = ble_event.evt.gattc_evt.params.read_rsp
                for obs in self.observers:
                    obs.on_gattc_evt_read_rsp(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        error_handle=ble_event.evt.gattc_evt.error_handle,
                        attr_handle=read_rsp_evt.handle,
                        offset=read_rsp_evt.offset,
                        data=util.uint8_array_to_list(
                            read_rsp_evt.data, read_rsp_evt.len
                        ),
                    )

            elif evt_id == BLEEvtID.gattc_evt_hvx:
                hvx_evt = ble_event.evt.gattc_evt.params.hvx
                for obs in self.observers:
                    obs.on_gattc_evt_hvx(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        error_handle=ble_event.evt.gattc_evt.error_handle,
                        attr_handle=hvx_evt.handle,
                        hvx_type=BLEGattHVXType(hvx_evt.type),
                        data=util.uint8_array_to_list(hvx_evt.data, hvx_evt.len),
                    )

            elif evt_id == BLEEvtID.gattc_evt_prim_srvc_disc_rsp:
                prim_srvc_disc_rsp_evt = (
                    ble_event.evt.gattc_evt.params.prim_srvc_disc_rsp
                )

                services = list()
                for s in util.service_array_to_list(
                    prim_srvc_disc_rsp_evt.services, prim_srvc_disc_rsp_evt.count
                ):
                    services.append(BLEService.from_c(s))

                for obs in self.observers:
                    obs.on_gattc_evt_prim_srvc_disc_rsp(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        services=services,
                    )

            elif evt_id == BLEEvtID.gattc_evt_char_disc_rsp:
                char_disc_rsp_evt = ble_event.evt.gattc_evt.params.char_disc_rsp

                characteristics = list()
                for ch in util.ble_gattc_char_array_to_list(
                    char_disc_rsp_evt.chars, char_disc_rsp_evt.count
                ):
                    characteristics.append(BLECharacteristic.from_c(ch))

                for obs in self.observers:
                    obs.on_gattc_evt_char_disc_rsp(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        characteristics=characteristics,
                    )

            elif evt_id == BLEEvtID.gattc_evt_desc_disc_rsp:
                desc_disc_rsp_evt = ble_event.evt.gattc_evt.params.desc_disc_rsp

                descriptors = list()
                for d in util.desc_array_to_list(
                    desc_disc_rsp_evt.descs, desc_disc_rsp_evt.count
                ):
                    descriptors.append(BLEDescriptor.from_c(d))

                for obs in self.observers:
                    obs.on_gattc_evt_desc_disc_rsp(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gattc_evt.conn_handle,
                        status=BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                        descriptors=descriptors,
                    )

            elif evt_id == BLEEvtID.gatts_evt_hvc:
                hvc_evt = ble_event.evt.gatts_evt.params.hvc

                for obs in self.observers:
                    obs.on_gatts_evt_hvc(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gatts_evt.conn_handle,
                        attr_handle=hvc_evt.handle,
                    )

            elif evt_id == BLEEvtID.gatts_evt_write:
                write_evt = ble_event.evt.gatts_evt.params.write

                for obs in self.observers:
                    obs.on_gatts_evt_write(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gatts_evt.conn_handle,
                        attr_handle=write_evt.handle,
                        uuid=write_evt.uuid,
                        op=write_evt.op,
                        auth_required=write_evt.auth_required,
                        offset=write_evt.offset,
                        length=write_evt.len,
                        data=write_evt.data,
                    )

            elif evt_id == BLEEvtID.gatts_evt_sys_attr_missing:
                sys_attr_missing_evt = ble_event.evt.gatts_evt.params.sys_attr_missing

                for obs in self.observers:
                    obs.on_gatts_evt_sys_attr_missing(
                        ble_driver=self,
                        conn_handle=ble_event.evt.gatts_evt.conn_handle,
                        hint=sys_attr_missing_evt.hint
                    )

            elif nrf_sd_ble_api_ver == 2:
                if evt_id == BLEEvtID.evt_tx_complete:
                    for obs in self.observers:
                        obs.on_evt_tx_complete(
                            ble_driver=self,
                            conn_handle=ble_event.evt.common_evt.conn_handle,
                            count=ble_event.evt.common_evt.params.tx_complete.count,
                        )

            elif nrf_sd_ble_api_ver == 5:
                if evt_id == BLEEvtID.gattc_evt_write_cmd_tx_complete:
                    tx_complete_evt = (
                        ble_event.evt.gattc_evt.params.write_cmd_tx_complete
                    )

                    for obs in self.observers:
                        obs.on_gattc_evt_write_cmd_tx_complete(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gattc_evt.conn_handle,
                            count=tx_complete_evt.count,
                        )

                elif evt_id == BLEEvtID.gatts_evt_hvn_tx_complete:
                    tx_complete_evt = ble_event.evt.gatts_evt.params.hvn_tx_complete

                    for obs in self.observers:
                        obs.on_gatts_evt_hvn_tx_complete(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gatts_evt.conn_handle,
                            count=tx_complete_evt.count,
                        )
                elif evt_id == BLEEvtID.gatts_evt_exchange_mtu_request:
                    for obs in self.observers:
                        obs.on_gatts_evt_exchange_mtu_request(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gatts_evt.conn_handle,
                            client_mtu=ble_event.evt.gatts_evt.params.exchange_mtu_request.client_rx_mtu,
                        )

                elif evt_id == BLEEvtID.gattc_evt_exchange_mtu_rsp:
                    xchg_mtu_evt = ble_event.evt.gattc_evt.params.exchange_mtu_rsp
                    _status = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status)
                    _server_rx_mtu = 0

                    if _status == BLEGattStatusCode.success:
                        _server_rx_mtu = xchg_mtu_evt.server_rx_mtu
                    else:
                        _server_rx_mtu = ATT_MTU_DEFAULT

                    for obs in self.observers:
                        obs.on_gattc_evt_exchange_mtu_rsp(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gattc_evt.conn_handle,
                            status=BLEGattStatusCode(
                                ble_event.evt.gattc_evt.gatt_status
                            ),
                            att_mtu=_server_rx_mtu,
                        )

                elif evt_id == BLEEvtID.gap_evt_data_length_update:
                    params = (
                        ble_event.evt.gap_evt.params.data_length_update.effective_params
                    )
                    for obs in self.observers:
                        obs.on_gap_evt_data_length_update(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gap_evt.conn_handle,
                            data_length_params=BLEGapDataLengthParams.from_c(params),
                        )

                elif evt_id == BLEEvtID.gap_evt_data_length_update_request:
                    params = (
                        ble_event.evt.gap_evt.params.data_length_update_request.peer_params
                    )
                    for obs in self.observers:
                        obs.on_gap_evt_data_length_update_request(
                            ble_driver=self,
                            conn_handle=ble_event.evt.gap_evt.conn_handle,
                            data_length_params=BLEGapDataLengthParams.from_c(params),
                        )

                elif evt_id == BLEEvtID.gap_evt_phy_update_request:
                    requested_phy_update = ble_event.evt.gap_evt.params.phy_update_request

                    for obs in self.observers:
                        obs.on_gap_evt_phy_update_request(
                            ble_driver=self,
                            conn_handle=ble_event.evt.common_evt.conn_handle,
                            peer_preferred_phys=BLEGapPhys.from_c(requested_phy_update.peer_preferred_phys)
                        )

                elif evt_id == BLEEvtID.gap_evt_phy_update:
                    updated_phy = ble_event.evt.gap_evt.params.phy_update

                    for obs in self.observers:
                        obs.on_gap_evt_phy_update(
                            ble_driver=self,
                            conn_handle=ble_event.evt.common_evt.conn_handle,
                            status=BLEHci(updated_phy.status),
                            tx_phy=updated_phy.tx_phy,
                            rx_phy=updated_phy.rx_phy,
                        )

        except Exception as e:
            logger.error("Exception: {}".format(str(e)))
            for line in traceback.extract_tb(sys.exc_info()[2]):
                logger.error(line)
            logger.error("")


class Flasher(object):
    api_lock = Lock()

    @staticmethod
    def which(program):
        import os

        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

        return None

    NRFJPROG = "nrfjprog"
    FW_STRUCT_LENGTH = 24
    FW_MAGIC_NUMBER = ["17", "A5", "D8", "46"]

    @staticmethod
    def fw_struct_address():
        # SoftDevice v2 and v5 has different
        # flash location for info struct
        if nrf_sd_ble_api_ver == 2:
            return 0x39000
        elif nrf_sd_ble_api_ver == 5:
            return 0x50000
        else:
            raise NordicSemiException(
                "Magic number for SDv{} is unknown.".format(nrf_sd_ble_api_ver)
            )

    @staticmethod
    def parse_fw_struct(raw_data):
        return {
            'len': len(raw_data),
            'magic_number': raw_data[:4],
            'version': '.'.join(str(int(raw_data[i], 16)) for i in (12, 13, 14)),
            'baud_rate': int("".join(raw_data[20:24][::-1]), 16),
            'api_version': int(raw_data[16], 16),
        }

    def __init__(self, serial_port=None, snr=None):
        if serial_port is None and snr is None:
            raise NordicSemiException("Invalid Flasher initialization")

        # cross-platform support: cast the params to string in case of unicode type coming from shell
        if serial_port is not None:
            serial_port = str(serial_port)
        if snr is not None:
            snr = str(snr)

        nrfjprog = Flasher.which(Flasher.NRFJPROG)
        if nrfjprog is None:
            nrfjprog = Flasher.which("{}.exe".format(Flasher.NRFJPROG))
            if nrfjprog is None:
                raise NordicSemiException("nrfjprog not installed")

        serial_ports = BLEDriver.enum_serial_ports()
        try:
            if serial_port is None:
                # Depending of platform and python version, serial_number may be padded with '0' up to 12 chars
                serial_port = [d.port for d in serial_ports if d.serial_number == snr or
                                                               d.serial_number == snr.rjust(12, '0')][0]
            elif snr is None:
                snr = [d.serial_number for d in serial_ports if d.port == serial_port][0]
        except IndexError:
            raise NordicSemiException("Board not found: {}".format(serial_port or snr))

        self.serial_port = serial_port
        self.snr = snr.lstrip("0")
        self.family = config.__conn_ic_id__

    def fw_check(self):
        fw_struct = Flasher.parse_fw_struct(self.read_fw_struct())
        return (
            Flasher.FW_STRUCT_LENGTH == fw_struct['len']
            and Flasher.is_valid_magic_number(fw_struct['magic_number'])
            and Flasher.is_valid_version(fw_struct['version'])
            and Flasher.is_valid_baud_rate(fw_struct['baud_rate'])
            and Flasher.is_valid_api_version(fw_struct['api_version'])
        )

    def fw_flash(self):
        self.erase()
        hex_file = config.conn_ic_hex_get()
        self.program(hex_file)

    def read_fw_struct(self):
        args = [
            "--memrd",
            str(Flasher.fw_struct_address()),
            "--w",
            "8",
            "--n",
            str(Flasher.FW_STRUCT_LENGTH),
        ]
        data = self.call_cmd(args)
        raw_data = []
        for line in data.splitlines():
            line = re.sub(r"(^.*:)|(\|.*$)", "", str(line))
            raw_data.extend(line.split())
        return raw_data

    def reset(self):
        args = ["--reset"]
        self.call_cmd(args)

    def erase(self):
        args = ["--eraseall"]
        self.call_cmd(args)

    def program(self, path):
        args = ["--program", path]
        self.call_cmd(args)

    @wrapt.synchronized(api_lock)
    def call_cmd(self, args):
        args = [Flasher.NRFJPROG, "--snr", str(self.snr)] + args + ["--family"] + [self.family]
        argstr = " ".join(args)
        try:
            return subprocess.check_output(argstr, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            if e.returncode == 18:
                raise RuntimeError(f"Invalid Connectivity IC ID: {self.family}")
            else:
                raise RuntimeError(f"{e.__str__()}\n{e.output}")

    @staticmethod
    def is_valid_magic_number(magic_number):
        return Flasher.FW_MAGIC_NUMBER == magic_number

    @staticmethod
    def is_valid_version(version):
        return config.get_connectivity_hex_version() == version

    @staticmethod
    def is_valid_baud_rate(baud_rate):
        return config.get_connectivity_hex_baud_rate() == baud_rate

    @staticmethod
    def is_valid_api_version(api_version):
        return nrf_sd_ble_api_ver == api_version
