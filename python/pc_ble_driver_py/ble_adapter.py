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
import Queue
import logging
import wrapt
from threading  import Condition, Lock
from ble_driver import *
from exceptions import NordicSemiException

from observers import *

logger  = logging.getLogger(__name__)

class DbConnection(object):
    def __init__(self):
        self.services     = list()
        self.att_mtu      = ATT_MTU_DEFAULT


    def get_char_value_handle(self, uuid):
        assert isinstance(uuid, BLEUUID), 'Invalid argument type'

        for s in self.services:
            for c in s.chars:
                if (c.uuid.value == uuid.value) and (c.uuid.base.type == uuid.base.type):
                    for d in c.descs:
                        if d.uuid.value == uuid.value:
                            return d.handle
        return None


    def get_cccd_handle(self, uuid):
        assert isinstance(uuid, BLEUUID), 'Invalid argument type'

        for s in self.services:
            for c in s.chars:
                if (c.uuid.value == uuid.value) and (c.uuid.base.type == uuid.base.type):
                    for d in c.descs:
                        if (d.uuid.value == BLEUUID.Standard.cccd):
                            return d.handle
                    break
        return None


    def get_char_handle(self, uuid):
        assert isinstance(uuid, BLEUUID), 'Invalid argument type'

        for s in self.services:
            for c in s.chars:
                if (c.uuid.value == uuid.value) and (c.uuid.base.type == uuid.base.type):
                    return c.handle_decl
        return None


    def get_char_uuid(self, handle):
        for s in self.services:
            for c in s.chars:
                if (c.handle_decl <= handle) and (c.end_handle >= handle):
                    return c.uuid


class EvtSync(object):
    def __init__(self, events):
        self.conds = dict()
        for evt in events:
            self.conds[evt] = Condition(Lock())
        self.data = None


    def wait(self, evt, timeout = 5):
        self.data = None
        with self.conds[evt]:
            self.conds[evt].wait(timeout=timeout)
            return self.data


    def notify(self, evt, data=None):
        with self.conds[evt]:
            self.data = data
            self.conds[evt].notify_all()


class BLEAdapter(BLEDriverObserver):
    observer_lock   = Lock()
    def __init__(self, ble_driver):
        super(BLEAdapter, self).__init__()
        self.driver             = ble_driver
        self.driver.observer_register(self)

        self.conn_in_progress   = False
        self.observers          = list()
        self.db_conns           = dict()
        self.evt_sync           = dict()


    def open(self):
        self.driver.open()


    def close(self):
        self.driver.close()
        self.conn_in_progress   = False
        self.db_conns           = dict()
        self.evt_sync           = dict()


    def connect(self, address, scan_params=None, conn_params=None):
        if self.conn_in_progress:
            return
        self.driver.ble_gap_connect(address     = address,
                                    scan_params = scan_params,
                                    conn_params = conn_params)
        self.conn_in_progress = True


    def disconnect(self, conn_handle):
        self.driver.ble_gap_disconnect(conn_handle)


    @wrapt.synchronized(observer_lock)
    def observer_register(self, observer):
        self.observers.append(observer)


    @wrapt.synchronized(observer_lock)
    def observer_unregister(self, observer):
        self.observers.remove(observer)


    def att_mtu_exchange(self, conn_handle):
        self.driver.ble_gattc_exchange_mtu_req(conn_handle)
        response = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_exchange_mtu_rsp)
        return self.db_conns[conn_handle].att_mtu


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def service_discovery(self, conn_handle, uuid=None):
        self.driver.ble_gattc_prim_srvc_disc(conn_handle, uuid, 0x0001)

        while True:
            response = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_prim_srvc_disc_rsp)

            if response['status'] == BLEGattStatusCode.success:
                self.db_conns[conn_handle].services.extend(response['services'])
            elif response['status'] == BLEGattStatusCode.attribute_not_found:
                break
            else:
                return response['status']

            if response['services'][-1].end_handle == 0xFFFF:
                break
            else:
                self.driver.ble_gattc_prim_srvc_disc(conn_handle,
                                                     uuid,
                                                     response['services'][-1].end_handle + 1)

        for s in self.db_conns[conn_handle].services:
            self.driver.ble_gattc_char_disc(conn_handle, s.start_handle, s.end_handle)
            while True:
                response = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_char_disc_rsp)

                if response['status'] == BLEGattStatusCode.success:
                    map(s.char_add, response['characteristics'])
                elif response['status'] == BLEGattStatusCode.attribute_not_found:
                    break
                else:
                    return response['status']

                self.driver.ble_gattc_char_disc(conn_handle,
                                                response['characteristics'][-1].handle_decl + 1,
                                                s.end_handle)

            for ch in s.chars:
                self.driver.ble_gattc_desc_disc(conn_handle, ch.handle_value, ch.end_handle)
                while True:
                    response = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_desc_disc_rsp)

                    if response['status'] == BLEGattStatusCode.success:
                        ch.descs.extend(response['descriptions'])
                    elif response['status'] == BLEGattStatusCode.attribute_not_found:
                        break
                    else:
                        return response['status']

                    if response['descriptions'][-1].handle == ch.end_handle:
                        break
                    else:
                        self.driver.ble_gattc_desc_disc(conn_handle,
                                                        response['descriptions'][-1].handle + 1,
                                                        ch.end_handle)
        return BLEGattStatusCode.success


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def enable_notification(self, conn_handle, uuid):
        cccd_list = [1, 0]

        handle = self.db_conns[conn_handle].get_cccd_handle(uuid)
        if handle == None:
            raise NordicSemiException('CCCD not found')

        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           handle,
                                           cccd_list,
                                           0)

        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def disable_notification(self, conn_handle, uuid):
        cccd_list = [0, 0]

        handle = self.db_conns[conn_handle].get_cccd_handle(uuid)
        if handle == None:
            raise NordicSemiException('CCCD not found')

        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           handle,
                                           cccd_list,
                                           0)

        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def enable_indication(self, conn_handle, uuid):
        cccd_list = [2, 0]

        handle = self.db_conns[conn_handle].get_cccd_handle(uuid)
        if handle == None:
            raise NordicSemiException('CCCD not found')

        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           handle,
                                           cccd_list,
                                           0)

        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def disable_indication(self, conn_handle, uuid):
        return self.disable_notification(conn_handle, uuid)


    def conn_param_update(self, conn_handle, conn_params):
        self.driver.ble_gap_conn_param_update(conn_handle, conn_params)


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def write_req(self, conn_handle, uuid, data):
        handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if handle == None:
            raise NordicSemiException('Characteristic value handler not found')
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.unused,
                                           handle,
                                           data,
                                           0)
        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']


    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def write_prep(self, conn_handle, uuid, data, offset):
        handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if handle == None:
            raise NordicSemiException('Characteristic value handler not found')
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.prepare_write_req,
                                           BLEGattExecWriteFlag.prepared_write,
                                           handle,
                                           data,
                                           offset)
        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']

    @NordicSemiErrorCheck(expected = BLEGattStatusCode.success)
    def write_exec(self, conn_handle):
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.execute_write_req,
                                           BLEGattExecWriteFlag.prepared_write,
                                           0,
                                           [],
                                           0)
        self.driver.ble_gattc_write(conn_handle, write_params)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_write_rsp)
        return result['status']

    def read_req(self, conn_handle, uuid):
        handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if handle == None:
            raise NordicSemiException('Characteristic value handler not found')
        self.driver.ble_gattc_read(conn_handle, handle,0)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gattc_evt_read_rsp)
        gatt_res = result['status']
        if gatt_res == BLEGattStatusCode.success:
             return (gatt_res, result['data'])
        else:
             return (gatt_res, None)

    def write_cmd(self, conn_handle, uuid, data):
        handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if handle == None:
            raise NordicSemiException('Characteristic value handler not found')
        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_cmd,
                                           BLEGattExecWriteFlag.unused,
                                           handle,
                                           data,
                                           0)

        # Send packet and skip waiting for TX-complete event. Try maximum 3 times.
        for _ in range(3):
            try:
                self.driver.ble_gattc_write(conn_handle, write_params)
                return
            except NordicSemiException as e:
                # Retry if BLE_ERROR_NO_TX_PACKETS error code.
                if "Error code: 12292" in e.message:
                    self.evt_sync[conn_handle].wait(evt=BLEEvtID.evt_tx_complete, timeout=1)
                else:
                    raise e
        raise NordicSemiException('Unable to successfully call ble_gattc_write')

    @NordicSemiErrorCheck(expected = BLEGapSecStatus.success)
    def authenticate(self, conn_handle):
        kdist_own   = BLEGapSecKDist(enc  = False,
                                     id   = False,
                                     sign = False,
                                     link = False)
        kdist_peer  = BLEGapSecKDist(enc  = False,
                                     id   = False,
                                     sign = False,
                                     link = False)
        sec_params  = BLEGapSecParams(bond          = False,
                                      mitm          = False,
                                      lesc          = False,
                                      keypress      = False,
                                      io_caps       = BLEGapIOCaps.none,
                                      oob           = False,
                                      min_key_size  = 7,
                                      max_key_size  = 16,
                                      kdist_own     = kdist_own,
                                      kdist_peer    = kdist_peer)

        self.driver.ble_gap_authenticate(conn_handle, sec_params)
        self.evt_sync[conn_handle].wait(evt = BLEEvtID.gap_evt_sec_params_request)

        self.driver.ble_gap_sec_params_reply(conn_handle, BLEGapSecStatus.success, None, None, None)
        result = self.evt_sync[conn_handle].wait(evt = BLEEvtID.gap_evt_auth_status)
        return result['auth_status']

    def on_evt_data_length_changed(self, ble_driver, **kwargs):
        for i in self.evt_sync:
            self.evt_sync[i].notify(evt=BLEEvtID.evt_data_length_changed, data=kwargs)

    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        self.db_conns[conn_handle]  = DbConnection()
        self.evt_sync[conn_handle]  = EvtSync(events = BLEEvtID)
        self.conn_in_progress       = False

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        del self.db_conns[conn_handle]
        del self.evt_sync[conn_handle]

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        if src == BLEGapTimeoutSrc.conn:
            self.conn_in_progress = False

    def on_gap_evt_sec_params_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gap_evt_sec_params_request, data = kwargs)

    def on_gap_evt_sec_info_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_sec_info_request, data=kwargs)

    def on_gap_evt_sec_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_sec_request, data=kwargs)

    def on_gap_evt_auth_status(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gap_evt_auth_status, data = kwargs)

    def on_gap_evt_auth_key_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_auth_key_request, data=kwargs)

    def on_evt_tx_complete(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.evt_tx_complete, data = kwargs)

    def on_gattc_evt_write_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_write_rsp, data = kwargs)

    def on_gattc_evt_read_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_read_rsp, data = kwargs)

    def on_gattc_evt_prim_srvc_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_prim_srvc_disc_rsp, data = kwargs)

    def on_gattc_evt_char_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_char_disc_rsp, data = kwargs)

    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_desc_disc_rsp, data = kwargs)

    def on_gatts_evt_hvc(self, ble_driver, status, error_handle, attr_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gatts_evt_hvc, data=kwargs)

    def on_gatts_evt_write(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gatts_evt_write, data=kwargs)

    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        self.db_conns[conn_handle].att_mtu = att_mtu

    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt = BLEEvtID.gattc_evt_exchange_mtu_rsp, data = kwargs)

    @wrapt.synchronized(observer_lock)
    def on_gap_evt_conn_param_update_request(self, ble_driver, conn_handle, conn_params):
        for obs in self.observers:
            obs.on_conn_param_update_request(ble_adapter = self,
                                             conn_handle = conn_handle, 
                                             conn_params = conn_params)

    @wrapt.synchronized(observer_lock)
    def on_gattc_evt_hvx(self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        if status != BLEGattStatusCode.success:
            logger.error("Error. Handle value notification failed. Status {}.".format(status))
            return

        if hvx_type == BLEGattHVXType.notification:
            uuid = self.db_conns[conn_handle].get_char_uuid(attr_handle)
            if uuid == None:
                raise NordicSemiException('UUID not found')

            for obs in self.observers:
                obs.on_notification(ble_adapter = self,
                                    conn_handle = conn_handle, 
                                    uuid        = uuid,
                                    data        = data)

        elif hvx_type == BLEGattHVXType.indication:
            uuid = self.db_conns[conn_handle].get_char_uuid(attr_handle)
            if uuid == None:
                raise NordicSemiException('UUID not found')

            for obs in self.observers:
                obs.on_indication(ble_adapter = self,
                                  conn_handle = conn_handle, 
                                  uuid        = uuid,
                                  data        = data)

            self.driver.ble_gattc_hv_confirm(conn_handle, attr_handle)
