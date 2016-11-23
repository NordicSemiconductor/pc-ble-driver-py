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

from enum import IntEnum

from nrf_dll_load   import driver, util
from nrf_types      import *

# TODO:
# * Implement _all_ events from ble_gap.h, ble_common.h, ble_gattc.h, ...

class BLEEvent(object):
    evt_id = None

    def __init__(self, conn_handle):
        self.conn_handle = conn_handle

class EvtTxComplete(BLEEvent):
    evt_id = driver.BLE_EVT_TX_COMPLETE

    def __init__(self, conn_handle, count):
        super(EvtTxComplete, self).__init__(conn_handle)
        self.count = count

    @classmethod
    def from_c(cls, event):
        tx_complete_evt = event.evt.common_evt.params.tx_complete
        return cls(conn_handle  = event.evt.common_evt.conn_handle,
                   count        = tx_complete_evt.count)

    def __repr__(self):
        return "%s(conn_handle=%r, count=%r)" % (
                self.__class__.__name__, self.conn_handle, self.count)

class GapEvt(BLEEvent):
    pass

class GapEvtAdvReport(GapEvt):
    evt_id = driver.BLE_GAP_EVT_ADV_REPORT

    def __init__(self, conn_handle, peer_addr, rssi, adv_type, adv_data):
        # TODO: What? Adv event has conn_handle? Does not compute
        super(GapEvtAdvReport, self).__init__(conn_handle)
        self.peer_addr      = peer_addr
        self.rssi           = rssi
        self.adv_type       = adv_type
        self.adv_data       = adv_data

    @classmethod
    def from_c(cls, event):
        adv_report_evt = event.evt.gap_evt.params.adv_report

        # TODO: adv_type what? We don't have a type for scan response?
        adv_type = None
        if not adv_report_evt.scan_rsp:
            adv_type = BLEGapAdvType(adv_report_evt.type)

        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   peer_addr    = BLEGapAddr.from_c(adv_report_evt.peer_addr),
                   rssi         = adv_report_evt.rssi,
                   adv_type     = adv_type,
                   adv_data     = BLEAdvData.from_c(adv_report_evt))

    def __repr__(self):
        return "%s(conn_handle=%r, peer_addr=%r, rssi=%r, adv_type=%r, adv_data=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.peer_addr, self.rssi, self.adv_type, self.adv_data)

class GapEvtTimeout(GapEvt):
    evt_id = driver.BLE_GAP_EVT_TIMEOUT

    def __init__(self, conn_handle, src):
        super(GapEvtTimeout, self).__init__(conn_handle)
        self.src = src

    @classmethod
    def from_c(cls, event):
        timeout_evt = event.evt.gap_evt.params.timeout
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   src          = BLEGapTimeoutSrc(timeout_evt.src))

    def __repr__(self):
        return "%s(conn_handle=%r, src=%r)" % (
                 self.__class__.__name__, self.conn_handle, self.src)

class GapEvtConnParamUpdateRequest(GapEvt):
    evt_id = driver.BLE_GAP_EVT_CONN_PARAM_UPDATE_REQUEST

    def __init__(self, conn_handle, conn_params):
        super(GapEvtConnParamUpdateRequest, self).__init__(conn_handle)
        self.conn_params = conn_params

    @classmethod
    def from_c(cls, event):
        conn_params = event.evt.gap_evt.params.conn_param_update_request.conn_params
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   conn_params  = BLEGapConnParams.from_c(conn_params))

    def __repr__(self):
        return "%s(conn_handle=%r, conn_params=%r)" % (
                self.__class__.__name__, self.conn_handle, self.conn_params)

class GapEvtConnParamUpdate(GapEvt):
    evt_id = driver.BLE_GAP_EVT_CONN_PARAM_UPDATE

    def __init__(self, conn_handle, conn_params):
        super(GapEvtConnParamUpdate, self).__init__(conn_handle)
        self.conn_params = conn_params

    @classmethod
    def from_c(cls, event):
        conn_params = event.evt.gap_evt.params.conn_param_update.conn_params
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   conn_params  = BLEGapConnParams.from_c(conn_params))

    def __repr__(self):
        return "%s(conn_handle=%r, conn_params=%r)" % (
                self.__class__.__name__, self.conn_handle, self.conn_params)


class GapEvtConnected(GapEvt):
    evt_id = driver.BLE_GAP_EVT_CONNECTED
    def __init__(self, conn_handle, peer_addr, own_addr, role, conn_params):
        super(GapEvtConnected, self).__init__(conn_handle)
        self.peer_addr      = peer_addr
        self.own_addr       = own_addr
        self.role           = role
        self.conn_params    = conn_params

    @classmethod
    def from_c(cls, event):
        connected_evt = event.evt.gap_evt.params.connected
        return cls(conn_handle    = event.evt.gap_evt.conn_handle,
                   peer_addr      = BLEGapAddr.from_c(connected_evt.peer_addr),
                   own_addr       = BLEGapAddr.from_c(connected_evt.own_addr),
                   role           = BLEGapRoles(connected_evt.role),
                   conn_params    = BLEGapConnParams.from_c(connected_evt.conn_params))

    def __repr__(self):
        return "%s(conn_handle=%r, peer_addr=%r, own_addr=%r, role=%r, conn_params=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.peer_addr, self.own_addr, self.role, self.conn_params)


class GapEvtDisconnected(GapEvt):
    evt_id = driver.BLE_GAP_EVT_DISCONNECTED

    def __init__(self, conn_handle, reason):
        super(GapEvtDisconnected, self).__init__(conn_handle)
        self.reason = reason

    @classmethod
    def from_c(cls, event):
        disconnected_evt = event.evt.gap_evt.params.disconnected
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   reason       = BLEHci(disconnected_evt.reason))

    def __repr__(self):
        return "%s(conn_handle=%r, reason=%r)" % (
                self.__class__.__name__, self.conn_handle, self.reason)


class GapEvtSec(GapEvt):
    pass

class GapEvtConnSecUpdate(GapEvtSec):
    evt_id = driver.BLE_GAP_EVT_CONN_SEC_UPDATE

    def __init__(self, conn_handle, sec_mode, sec_level, encr_key_size):
        super(GapEvtConnSecUpdate, self).__init__(conn_handle)
        self.sec_mode         = sec_mode
        self.sec_level        = sec_level
        self.encr_key_size    = encr_key_size

    @classmethod
    def from_c(cls, event):
        conn_sec = event.evt.gap_evt.params.conn_sec_update.conn_sec
        return cls(conn_handle      = event.evt.gap_evt.conn_handle,
                   sec_mode         = conn_sec.sec_mode.sm,
                   sec_level        = conn_sec.sec_mode.lv,
                   encr_key_size    = conn_sec.encr_key_size)

    def __repr__(self):
        return "%s(conn_handle=%r, sec_mode=%r, sec_level=%r, encr_key_size=%r)" % (
                self.__class__.__name__, self.conn_handle, self.sec_mode, self.sec_level, self.encr_key_size)

class GapEvtSecParamsRequest(GapEvtSec):
    evt_id = driver.BLE_GAP_EVT_SEC_PARAMS_REQUEST

    def __init__(self, conn_handle, sec_params):
        super(GapEvtSecParamsRequest, self).__init__(conn_handle)
        self.sec_params = sec_params

    @classmethod
    def from_c(cls, event):
        sec_params = event.evt.gap_evt.params.sec_params_request.peer_params
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   sec_params   = BLEGapSecParams.from_c(sec_params))

    def __repr__(self):
        return "%s(conn_handle=%r, sec_params=%r)" % ( self.__class__.__name__, self.conn_handle, self.sec_params)

# TODO: Move to nrf_types, merge with BLEGapIOCaps
class GapIoCaps(IntEnum):
    DISPLAY_ONLY        = driver.BLE_GAP_IO_CAPS_DISPLAY_ONLY
    DISPLAY_YESNO       = driver.BLE_GAP_IO_CAPS_DISPLAY_YESNO
    KEYBOARD_ONLY       = driver.BLE_GAP_IO_CAPS_KEYBOARD_ONLY
    NONE                = driver.BLE_GAP_IO_CAPS_NONE
    KEYBOARD_DISPLAY    = driver.BLE_GAP_IO_CAPS_KEYBOARD_DISPLAY

# TODO: Move to nrf_types
class GapAuthKeyType(IntEnum):
    NONE    = driver.BLE_GAP_AUTH_KEY_TYPE_NONE
    PASSKEY = driver.BLE_GAP_AUTH_KEY_TYPE_PASSKEY
    OOB     = driver.BLE_GAP_AUTH_KEY_TYPE_OOB

class GapEvtAuthKeyRequest(GapEvtSec):
    evt_id = driver.BLE_GAP_EVT_AUTH_KEY_REQUEST

    def __init__(self, conn_handle, key_type):
        super(GapEvtAuthKeyRequest, self).__init__(conn_handle)
        self.key_type = key_type

    @classmethod
    def from_c(cls, event):
        auth_key_request = event.evt.gap_evt.params.auth_key_request
        return cls(conn_handle = event.evt.gap_evt.conn_handle,
                   key_type    = GapAuthKeyType(auth_key_request.key_type))

    def __repr__(self):
        return "%s(conn_handle=%r, key_type=%r)" % ( self.__class__.__name__, self.conn_handle, self.key_type)

class GapEvtAuthStatus(GapEvtSec):
    evt_id = driver.BLE_GAP_EVT_AUTH_STATUS

    def __init__(self, conn_handle, auth_status, error_src, bonded, sm1_levels, sm2_levels, kdist_own, kdist_peer):
        super(GapEvtAuthStatus, self).__init__(conn_handle)
        self.auth_status    = auth_status
        self.error_src      = error_src
        self.bonded         = bonded
        self.sm1_levels     = sm1_levels
        self.sm2_levels     = sm2_levels
        self.kdist_own      = kdist_own
        self.kdist_peer     = kdist_peer

    @classmethod
    def from_c(cls, event):
        auth_status = event.evt.gap_evt.params.auth_status
        return cls(conn_handle  = event.evt.gap_evt.conn_handle,
                   auth_status  = auth_status.auth_status,
                   error_src    = auth_status.error_src,
                   bonded       = auth_status.bonded,
                   sm1_levels   = BLEGapSecLevels.from_c(auth_status.sm1_levels),
                   sm2_levels   = BLEGapSecLevels.from_c(auth_status.sm2_levels),
                   kdist_own    = BLEGapSecKeyDist.from_c(auth_status.kdist_own),
                   kdist_peer   = BLEGapSecKeyDist.from_c(auth_status.kdist_peer))

    def __str__(self):
        return "%s(conn_handle=%r, auth_status=%r, error_src=%r, bonded=%r, sm1_levels=%r, sm2_levels=%r, kdist_own=%r, kdist_peer=%r)" % (
                self.__class__.__name__, self.conn_handle, self.auth_status, self.error_src, self.bonded,
                self.sm1_levels, self.sm2_levels, self.kdist_own, self.kdist_peer)

class GattcEvt(BLEEvent):
    pass

class GattcEvtReadResponse(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_READ_RSP

    def __init__(self, conn_handle, status, error_handle, attr_handle, offset, data):
        super(GattcEvtReadResponse, self).__init__(conn_handle)
        self.status         = status
        self.error_handle   = error_handle
        self.attr_handle    = attr_handle
        self.offset         = offset
        if isinstance(data, str):
            self.data       = map(ord, data)
        else:
            self.data       = data

    @classmethod
    def from_c(cls, event):
        read_rsp = event.evt.gattc_evt.params.read_rsp
        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status       = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   error_handle = event.evt.gattc_evt.error_handle,
                   attr_handle  = read_rsp.handle,
                   offset       = read_rsp.offset,
                   data         = util.uint8_array_to_list(read_rsp.data, read_rsp.len))

    def __repr__(self):
        data = ''.join(map(chr, self.data))
        return "%s(conn_handle=%r, status=%r, error_handle=%r, attr_handle=%r, offset=%r, data=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.error_handle, self.attr_handle, self.offset, data)

class GattcEvtHvx(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_HVX

    def __init__(self, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        super(GattcEvtHvx, self).__init__(conn_handle)
        self.status         = status
        self.error_handle   = error_handle
        self.attr_handle    = attr_handle
        self.hvx_type       = hvx_type
        if isinstance(data, str):
            self.data       = map(ord, data)
        else:
            self.data       = data

    @classmethod
    def from_c(cls, event):
        hvx_evt = event.evt.gattc_evt.params.hvx
        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status       = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   error_handle = event.evt.gattc_evt.error_handle,
                   attr_handle  = hvx_evt.handle,
                   hvx_type     = BLEGattHVXType(hvx_evt.type),
                   data         = util.uint8_array_to_list(hvx_evt.data, hvx_evt.len))

    def __repr__(self):
        data = ''.join(map(chr, self.data))
        return "%s(conn_handle=%r, status=%r, error_handle=%r, attr_handle=%r, hvx_type=%r, data=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.error_handle, self.attr_handle, self.hvx_type, data)

class GattcEvtWriteResponse(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_WRITE_RSP

    def __init__(self, conn_handle, status, error_handle, attr_handle, write_op, offset, data):
        super(GattcEvtWriteResponse, self).__init__(conn_handle)
        self.status         = status
        self.error_handle   = error_handle
        self.attr_handle    = attr_handle
        self.write_op       = write_op
        self.offset         = offset
        if isinstance(data, str):
            self.data       = map(ord, data)
        else:
            self.data       = data

    @classmethod
    def from_c(cls, event):
        write_rsp_evt   = event.evt.gattc_evt.params.write_rsp
        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status       = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   error_handle = event.evt.gattc_evt.error_handle,
                   attr_handle  = write_rsp_evt.handle,
                   write_op     = BLEGattWriteOperation(write_rsp_evt.write_op),
                   offset       = write_rsp_evt.offset,
                   data         = util.uint8_array_to_list(write_rsp_evt.data, write_rsp_evt.len))

    def __repr__(self):
        data = ''.join(map(chr, self.data))
        return "%s(conn_handle=%r, status=%r, error_handle=%r, attr_handle=%r, write_op=%r, offset=%r, data=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.error_handle, self.attr_handle, self.write_op, self.offset, data)


class GattcEvtPrimaryServicecDiscoveryResponse(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_PRIM_SRVC_DISC_RSP

    def __init__(self, conn_handle, status, services):
        super(GattcEvtPrimaryServicecDiscoveryResponse, self).__init__(conn_handle)
        self.status         = status
        self.services       = services

    @classmethod
    def from_c(cls, event):
        prim_srvc_disc_rsp_evt = event.evt.gattc_evt.params.prim_srvc_disc_rsp

        services = list()
        for s in util.service_array_to_list(prim_srvc_disc_rsp_evt.services, prim_srvc_disc_rsp_evt.count):
            services.append(BLEService.from_c(s))

        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status       = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   services     = services)

    def __repr__(self):
        return "%s(conn_handle=%r, status=%r, services=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.services)

class GattcEvtCharacteristicDiscoveryResponse(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_CHAR_DISC_RSP

    def __init__(self, conn_handle, status, characteristics):
        super(GattcEvtCharacteristicDiscoveryResponse, self).__init__(conn_handle)
        self.status             = status
        self.characteristics    = characteristics

    @classmethod
    def from_c(cls, event):
        char_disc_rsp_evt = event.evt.gattc_evt.params.char_disc_rsp

        characteristics = list()
        for ch in util.ble_gattc_char_array_to_list(char_disc_rsp_evt.chars, char_disc_rsp_evt.count):
            characteristics.append(BLECharacteristic.from_c(ch))

        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status           = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   characteristics  = characteristics)

    def __repr__(self):
        return "%s(conn_handle=%r, status=%r, characteristics=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.characteristics)

class GattcEvtDescriptorDiscoveryResponse(GattcEvt):
    evt_id = driver.BLE_GATTC_EVT_DESC_DISC_RSP

    def __init__(self, conn_handle, status, descriptions):
        super(GattcEvtDescriptorDiscoveryResponse, self).__init__(conn_handle)
        self.status         = status
        self.descriptions   = descriptions

    @classmethod
    def from_c(cls, event):
        desc_disc_rsp_evt = event.evt.gattc_evt.params.desc_disc_rsp

        descriptions = list()
        for d in util.desc_array_to_list(desc_disc_rsp_evt.descs, desc_disc_rsp_evt.count):
            descriptions.append(BLEDescriptor.from_c(d))

        return cls(conn_handle  = event.evt.gattc_evt.conn_handle,
                   status       = BLEGattStatusCode(event.evt.gattc_evt.gatt_status),
                   descriptions = descriptions)

    def __repr__(self):
        return "%s(conn_handle=%r, status=%r, descriptions=%r)" % (
                self.__class__.__name__, self.conn_handle,
                self.status, self.descriptions)



def event_decode(ble_event):
    event_classes = [
            EvtTxComplete,

            # Gap
            GapEvtAdvReport,
            GapEvtConnected,
            GapEvtDisconnected,
            GapEvtTimeout,

            GapEvtConnParamUpdateRequest,
            GapEvtConnParamUpdate,

            # SMP
            GapEvtSecParamsRequest,
            GapEvtAuthKeyRequest,
            GapEvtConnSecUpdate,
            GapEvtAuthStatus,
            # driver.BLE_GAP_EVT_SEC_INFO_REQUEST,
            # driver.BLE_GAP_EVT_SEC_REQUEST,

            # Gattc
            GattcEvtReadResponse,
            GattcEvtHvx,
            GattcEvtWriteResponse,
            GattcEvtPrimaryServicecDiscoveryResponse,
            GattcEvtCharacteristicDiscoveryResponse,
            GattcEvtDescriptorDiscoveryResponse
            ]

    for event_class in event_classes:
        if ble_event.header.evt_id == event_class.evt_id:
            return event_class.from_c(ble_event)

