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

"""
This module implements convenience methods on top of ble_driver
"""

from threading import Condition
from queue import Queue
import logging

from pc_ble_driver_py.ble_driver import *
from pc_ble_driver_py.exceptions import NordicSemiException
from pc_ble_driver_py.observers import *

logger = logging.getLogger(__name__)

MAX_TRIES = 10  # Maximum Number of Tries by driver.ble_gattc_write


class DbConnection(object):
    def __init__(self):
        self.services = list()
        self.att_mtu = ATT_MTU_DEFAULT

    def get_char_value_handle(self, uuid, service_uuid=None):
        assert isinstance(uuid, BLEUUID), "Invalid argument type"

        if service_uuid is not None:
            assert isinstance(service_uuid, BLEUUID), "Invalid argument type"

        for s in self.services:
            if service_uuid is None or (
                (s.uuid.value == service_uuid.value)
                and (s.uuid.base.type == service_uuid.base.type)
            ):
                for c in s.chars:
                    if (c.uuid.value == uuid.value) and (
                        c.uuid.base.type == uuid.base.type
                    ):
                        for d in c.descs:
                            if d.uuid.value == uuid.value:
                                return d.handle
        return None

    def get_cccd_handle(self, uuid, attr_handle=None):
        assert isinstance(uuid, BLEUUID), "Invalid argument type"
        for s in self.services:
            for c in s.chars:
                if (c.char_props.notify == 1 or c.char_props.indicate == 1
                    ) and (c.uuid.value == uuid.value) and (
                    c.uuid.base.type == uuid.base.type):
                    if attr_handle is None:
                        for d in c.descs:
                            if d.uuid.value == BLEUUID.Standard.cccd:
                                return d.handle
                        break
                    elif attr_handle == c.handle_value:
                        for d in c.descs:
                            if d.uuid.value == BLEUUID.Standard.cccd:
                                return d.handle
        return None

    def get_char_handle(self, uuid):
        assert isinstance(uuid, BLEUUID), "Invalid argument type"

        for s in self.services:
            for c in s.chars:
                if (c.char_props.read == 1) and (
                    c.uuid.value == uuid.value) and (
                    c.uuid.base.type == uuid.base.type
                ):
                    return c.handle_decl
        return None

    def get_char_uuid(self, handle):
        for s in self.services:
            for c in s.chars:
                if (c.handle_decl <= handle) and (c.end_handle >= handle):
                    return c.uuid

    def get_char_props(self, handle):
        for s in self.services:
            for c in s.chars:
                if (c.handle_decl <= handle) and (c.end_handle >= handle):
                    return c.char_props


class Connection(DbConnection):
    def __init__(self, peer_addr, role):
        super(Connection, self).__init__()
        self.role = role
        self.peer_addr = peer_addr
        self._keyset = None

    def __str__(self):
        s = (
            "BLE Connection:{id}:\n"
            "  role: {role}\n"
            "  peer_addr: {peer_addr}\n"
            "  services:\n"
            "    {services}"
        )
        return s.format(
            id=id(self),
            role=self.role,
            peer_addr="{} ({})".format(self.peer_addr.addr, self.peer_addr.addr_type),
            services="\n    ".join(str(s) for s in self.services),
        )

    def __repr__(self):
        return self.__str__()


class EvtSync(object):
    def __init__(self, events):
        self.conds = dict()
        self.data = dict()
        for evt in events:
            self.conds[evt] = Condition(Lock())
            self.data[evt] = None
        
    def wait(self, evt, timeout=5):
        self.data[evt] = None
        with self.conds[evt]:
            self.conds[evt].wait(timeout=timeout)
            return self.data[evt]

    def notify(self, evt, data=None):
        with self.conds[evt]:
            self.data[evt] = data
            self.conds[evt].notify_all()
    
    def call(self, evt, func, timeout=5, **kwargs):
        with self.conds[evt]:
            self.data[evt] = None
            func(**kwargs)
            self.conds[evt].wait(timeout)
            return self.data[evt]


class BLEAdapter(BLEDriverObserver):
    observer_lock = Lock()

    def __init__(self, ble_driver):
        super(BLEAdapter, self).__init__()
        self.driver = ble_driver
        self.driver.observer_register(self)

        self.is_opened = False
        self.is_init_ok = False
        self.is_scan_timeout = False
        self.scan_q = Queue()
        self.conn_handle = -1
        self.is_connected = False
        self.observers = list()
        self.db_conns = dict()
        self.evt_sync = dict()
        self.default_mtu = ATT_MTU_DEFAULT    

    def connect_required(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_connected:
                raise NordicSemiException("Error! Disconnected from server.")
            return func(self, *args, **kwargs)
        return wrapper


    def get_version(self):
        if not self.is_init_ok:
            return None
        return self.driver.ble_version_get()

    def open(self):
        try:
            self.driver.open()
            self.is_opened=True
            return True
        except NordicSemiException as e:
            return False

    def close(self):
        self.driver.close()
        self.is_opened = False
        self.is_init_ok = False
        self.is_connected = False
        self.db_conns = dict()
        self.evt_sync = dict()
    
    def ble_cfg_set(self,cfg_id,cfg):
        if not self.is_opened:
            return False
        if nrf_sd_ble_api_ver == 5:
            self.driver.ble_cfg_set(cfg_id, cfg)

    def ble_stack_init(self,cfg=None):
        if not self.is_opened:
            return False
        if nrf_sd_ble_api_ver == 2:
            if not cfg:
                cfg=BLEEnableParams(vs_uuid_count=1,
                                service_changed=0,
                                periph_conn_count=1,
                                central_conn_count=1,
                                central_sec_count=1)
            self.driver.ble_enable(cfg)
        elif nrf_sd_ble_api_ver == 5:
            if not cfg:
                cfg = BLEConfigConnGatt()
                cfg.att_mtu = self.default_mtu
            self.ble_cfg_set(BLEConfig.conn_gatt, cfg)
            self.driver.ble_enable()
        self.is_init_ok=True
        return True

    def scan(self, filter_by_name_or_address, value_to_find, scan_params=None):
        if not self.is_init_ok:
            return None
        self.is_scan_timeout=False
        self.is_connected = False
        #clear 'scan_q'
        while not self.scan_q.empty():
            self.scan_q.get()
        #get default 'scan_params'
        if not scan_params:
            scan_patams = BLEGapScanParams(interval_ms=200, window_ms=150, timeout_s=5)
        self.driver.ble_gap_scan_start(scan_params=scan_params)
        peer_addr=None
        is_find=False
        scan_duration=scan_patams.timeout_s #scan timeout
        time_beg=time.time()
        while 0<= time.time()-time_beg <= scan_duration*2:
            if not self.scan_q.empty():
                dict_data=self.scan_q.get()
            else: #empty
                if self.is_scan_timeout:
                    return None
                else:
                    continue
   
            if filter_by_name_or_address.lower() == "name":
                peer_addr = dict_data["peer_addr"]
                dict_adv_records=dict_data["adv_data"].records
                if BLEAdvData.Types.complete_local_name in dict_adv_records.keys():
                    dev_name_list = dict_adv_records[BLEAdvData.Types.complete_local_name]
                elif BLEAdvData.Types.short_local_name in dict_adv_records.keys():
                    dev_name_list = dict_adv_records[BLEAdvData.Types.short_local_name]
                else:
                    continue
                dev_name = "".join(chr(e) for e in dev_name_list)
                if dev_name == value_to_find:
                    is_find = True
                    break
                    
            else:
                peer_addr = dict_data["peer_addr"]
                address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
              
                if address_string == value_to_find.replace(":","").upper():
                    is_find = True
                    break
        
        if is_find:
            self.driver.ble_gap_scan_stop()
            return peer_addr
        else:
            return None
    
    def connect(self, address, scan_params=None, conn_params=None, tag=0):
        if not self.is_init_ok:
            return False
        if self.is_connected:
            return True
        if nrf_sd_ble_api_ver == 2:
            self.driver.ble_gap_connect(
                address=address, scan_params=scan_params, conn_params=conn_params
            )
        elif nrf_sd_ble_api_ver == 5:
            self.driver.ble_gap_connect(
                address=address,
                scan_params=scan_params,
                conn_params=conn_params,
                tag=tag,
            )
        if not conn_params:
            conn_params=self.driver.conn_params_setup()
        conn_timeout_s=conn_params.conn_sup_timeout_ms/1000
        time_beg=time.time()
        while 0<= time.time()-time_beg <= conn_timeout_s+2:
            if self.is_connected:
                break
        return self.is_connected

    @connect_required
    def disconnect(self, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        self.driver.ble_gap_disconnect(conn_handle)
        time_beg=time.time()
        while 0<= time.time()-time_beg <= 4:
            if not self.is_connected:
                break
        return (not self.is_connected)


    @wrapt.synchronized(observer_lock)
    def observer_register(self, observer):
        self.observers.append(observer)

    @wrapt.synchronized(observer_lock)
    def observer_unregister(self, observer):
        self.observers.remove(observer)

    @connect_required
    def att_mtu_exchange(self, mtu, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        try:
            response = self.evt_sync[conn_handle].call(
                evt=BLEEvtID.gattc_evt_exchange_mtu_rsp,
                func=self.driver.ble_gattc_exchange_mtu_req,
                conn_handle=conn_handle,
                mtu=mtu)

        except NordicSemiException as ex:
            raise NordicSemiException(
                "MTU exchange request failed. Common causes are: "
                "missing att_mtu setting in ble_cfg_set, "
                "different config tags used in ble_cfg_set and connect.") from ex

        
        if response is None:
            return self.db_conns[conn_handle].att_mtu

        # Use minimum of client and server mtu to ensure both sides support the value
        new_mtu = min(mtu, response["att_mtu"])
        logger.debug(f"New ATT MTU is {new_mtu}")
        self.db_conns[conn_handle].att_mtu = new_mtu
        return new_mtu

    @connect_required
    def phy_update(self, req_phys, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        try:
            gap_phys = BLEGapPhys(*req_phys)
            response = self.evt_sync[conn_handle].call(
                evt=BLEEvtID.gap_evt_phy_update,
                func=self.driver.ble_gap_phy_update,
                conn_handle=conn_handle,
                gap_phys=gap_phys)
        except NordicSemiException as ex:
            raise ex

        return response

    @connect_required
    def data_length_update(self, data_length, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        try:
            dl_params = BLEGapDataLengthParams()
            dl_params.max_tx_octets = data_length
            dl_params.max_rx_octets = data_length
            response = self.evt_sync[conn_handle].call(
                evt=BLEEvtID.gap_evt_data_length_update,
                func=self.driver.ble_gap_data_length_update,
                conn_handle=conn_handle,
                data_length_params=dl_params,
                data_length_limitation=None)
        except NordicSemiException as ex:
            raise ex

        if response and "data_length_params" in response:
            max_tx_octets = response["data_length_params"].max_tx_octets
            logger.debug(f"New Data Length is {max_tx_octets}")
            return response["data_length_params"]
        else:
            return None

    @connect_required
    def service_discovery(self, uuid=None, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        # Don't add repeat handles
        # See: https://github.com/NordicSemiconductor/pc-ble-driver-py/issues/219
        if uuid is not None and uuid in [service.uuid for service in self.db_conns[conn_handle].services]:
            return BLEGattStatusCode.success
        
        vendor_services = []
        start_handle=0x0001
        while True:
            if conn_handle in self.evt_sync.keys():
                response = self.evt_sync[conn_handle].call(
                    evt=BLEEvtID.gattc_evt_prim_srvc_disc_rsp,
                    func=self.driver.ble_gattc_prim_srvc_disc,
                    conn_handle=conn_handle,
                    srvc_uuid=uuid,
                    start_handle=start_handle
                )
                if response:
                    if response["status"] == BLEGattStatusCode.success:
                        for s in response["services"]:
                            # Don't add repeat handles
                            # See: https://github.com/NordicSemiconductor/pc-ble-driver-py/issues/219
                            if s.uuid not in [service.uuid for service in self.db_conns[conn_handle].services]:
                                if s.uuid.value == BLEUUID.Standard.unknown:
                                    vendor_services.append(s)
                                else:
                                    self.db_conns[conn_handle].services.append(s)
                    elif response["status"] == BLEGattStatusCode.attribute_not_found:
                        break
                    else:
                        return response["status"]

                    if response["services"][-1].end_handle == 0xFFFF:
                        break
                    else:
                        start_handle = response["services"][-1].end_handle + 1
                        
            else:
                raise NordicSemiException(
                    "conn_handle not available. common cause is disconnect after"
                    "starting service_discovery")


        for s in vendor_services:
            # Read service handle to obtain full 128-bit UUID.
            response = self.evt_sync[conn_handle].call(
                evt=BLEEvtID.gattc_evt_read_rsp,
                func=self.driver.ble_gattc_read,
                conn_handle=conn_handle,
                handle=s.start_handle,
                offset=0)
            if response:
                if response["status"] != BLEGattStatusCode.success:
                    continue

                # Check response length.
                if len(response["data"]) != 16:
                    continue

                # Create UUIDBase object and register it in softdevice
                base = BLEUUIDBase(
                    response["data"][::-1], driver.BLE_UUID_TYPE_VENDOR_BEGIN
                )
                self.driver.ble_vs_uuid_add(base)

                # Rediscover this service.
                response = self.evt_sync[conn_handle].call(
                    evt=BLEEvtID.gattc_evt_prim_srvc_disc_rsp,
                    func=self.driver.ble_gattc_prim_srvc_disc,
                    conn_handle=conn_handle,
                    srvc_uuid=uuid,
                    start_handle=s.start_handle
                )
                if response and response["status"] == BLEGattStatusCode.success:
                    # Assign UUIDBase manually
                    # See:
                    #  https://github.com/NordicSemiconductor/pc-ble-driver-py/issues/38
                    for s.uuid in [service.uuid for service in response["services"]]:
                        s.uuid.base = base
                    self.db_conns[conn_handle].services.extend(response["services"])
        
        #discovery characteristics
        for s in self.db_conns[conn_handle].services:
            start_handle = s.start_handle
            while True:
                response = self.evt_sync[conn_handle].call(
                    evt=BLEEvtID.gattc_evt_char_disc_rsp,
                    func=self.driver.ble_gattc_char_disc,
                    conn_handle=conn_handle, 
                    start_handle=start_handle, 
                    end_handle=s.end_handle

                )
                if response and "status" in response.keys():
                    if response["status"] == BLEGattStatusCode.success:
                        for char in response["characteristics"]:
                            # Don't add repeat handles
                            # See: https://github.com/NordicSemiconductor/pc-ble-driver-py/issues/219
                            if char.uuid not in [c.uuid for c in s.chars]:
                                s.char_add(char)
                    elif response["status"] == BLEGattStatusCode.attribute_not_found:
                        break
                    else:
                        return response["status"]

                    start_handle = response["characteristics"][-1].handle_decl + 1

            #discovery descriptors
            for ch in s.chars:
                start_handle = ch.handle_value
                while True:
                    response = self.evt_sync[conn_handle].call(
                        evt=BLEEvtID.gattc_evt_desc_disc_rsp,
                        func=self.driver.ble_gattc_desc_disc,
                        conn_handle=conn_handle, 
                        start_handle=start_handle, 
                        end_handle=ch.end_handle
                    )
                    if response and "status" in response.keys():
                        if response["status"] == BLEGattStatusCode.success:
                            for desc in response["descriptors"]:
                                # Don't add repeat handles
                                # See: https://github.com/NordicSemiconductor/pc-ble-driver-py/issues/219
                                if desc not in [d.uuid for d in ch.descs]:
                                    ch.descs.append(desc)
                        elif response["status"] == BLEGattStatusCode.attribute_not_found:
                            break
                        else:
                            return response["status"]

                        if response["descriptors"][-1].handle == ch.end_handle:
                            break
                        else:
                            start_handle = response["descriptors"][-1].handle + 1
        
                               
        return BLEGattStatusCode.success

    @connect_required
    def cccd_ctrl(self, cccd_list, uuid, conn_handle=None, attr_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        assert isinstance(cccd_list, list), "Invalid argument type"
        assert isinstance(uuid, BLEUUID), "Invalid argument type"

        if uuid.base.base is not None and uuid.base.type is None:
            self.driver.ble_uuid_decode(uuid.base.base, uuid)
        cccd_handle = self.db_conns[conn_handle].get_cccd_handle(uuid, attr_handle)
        if cccd_handle is None:
            raise NordicSemiException("CCCD not found")
        write_params = BLEGattcWriteParams(
            BLEGattWriteOperation.write_req,
            BLEGattExecWriteFlag.unused,
            cccd_handle,
            cccd_list,
            0,
        )

        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gattc_evt_write_rsp,
            func=self.driver.ble_gattc_write,
            conn_handle=conn_handle, 
            write_params=write_params
            )
        if result and "status" in result:
            return result["status"]
        else:
            return None


    def enable_notification(self, uuid, conn_handle=None, attr_handle=None):
        return self.cccd_ctrl([1, 0], uuid, conn_handle, attr_handle)

    def disable_notification(self, uuid, conn_handle=None, attr_handle=None):
        return self.cccd_ctrl([0, 0], uuid, conn_handle, attr_handle)

    def enable_indication(self, uuid, conn_handle=None, attr_handle=None):
        return self.cccd_ctrl([2, 0], uuid, conn_handle, attr_handle)

    def disable_indication(self, uuid, conn_handle=None, attr_handle=None):
        return self.cccd_ctrl([0, 0], uuid, conn_handle, attr_handle)

    @connect_required
    def conn_param_update(self, conn_params, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gap_evt_conn_param_update,
            func=self.driver.ble_gap_conn_param_update,
            conn_handle=conn_handle, 
            conn_params=conn_params
            )
        if result and "conn_params" in result:
            return result["conn_params"]
        else:
            return None

    @connect_required
    def write_req(self, uuid, data, conn_handle=None, attr_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        if attr_handle is None:
            attr_handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if attr_handle is None:
            raise NordicSemiException("Characteristic value handler not found")
        
        send_len=0
        data_len=len(data)
        while data_len > send_len:
            if data_len-send_len > self.db_conns[conn_handle].att_mtu-3:
                sub_len=self.db_conns[conn_handle].att_mtu-3
            else:
                sub_len=data_len-send_len
            sub_data=data[send_len:send_len+sub_len]
            write_params = BLEGattcWriteParams(
                BLEGattWriteOperation.write_req,
                BLEGattExecWriteFlag.unused,
                attr_handle,
                sub_data,
                0
            )
            result = self.evt_sync[conn_handle].call(
                evt=BLEEvtID.gattc_evt_write_rsp,
                func=self.driver.ble_gattc_write,
                conn_handle=conn_handle, 
                write_params=write_params
                )
            send_len += sub_len
            if result and "status" in result.keys() and result["status"] == BLEGattStatusCode.success:
                continue
            else:
                break
        
        if result and "status" in result.keys():
            return result["status"]
        else:
            return None

    @connect_required
    def write_prep(self, uuid, data, offset, conn_handle=None, attr_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        if attr_handle is None:
            attr_handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if attr_handle is None:
            raise NordicSemiException("Characteristic value handler not found")
        write_params = BLEGattcWriteParams(
            BLEGattWriteOperation.prepare_write_req,
            BLEGattExecWriteFlag.prepared_write,
            attr_handle,
            data,
            offset,
        )
        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gattc_evt_write_rsp,
            func=self.driver.ble_gattc_write,
            conn_handle=conn_handle, 
            write_params=write_params
            )
        if result and "status" in result:
            return result["status"]
        else:
            return None

    @connect_required
    def write_exec(self, conn_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        write_params = BLEGattcWriteParams(
            BLEGattWriteOperation.execute_write_req,
            BLEGattExecWriteFlag.prepared_write,
            0,
            [],
            0,
        )
        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gattc_evt_write_rsp,
            func=self.driver.ble_gattc_write,
            conn_handle=conn_handle, 
            write_params=write_params
            )
        if result and "status" in result:
            return result["status"]
        else:
            return None

    @connect_required
    def read_req(self, uuid, conn_handle=None, offset=0, attr_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        if attr_handle is None:
            attr_handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if attr_handle is None:
            raise NordicSemiException("Characteristic value handler not found")
        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gattc_evt_read_rsp,
            func=self.driver.ble_gattc_read,
            conn_handle=conn_handle, 
            handle=attr_handle, 
            offset=offset
            )
        if not result or "status" not in result:
            return None, None

        gatt_res = result["status"]
        if gatt_res == BLEGattStatusCode.success:
            return gatt_res, result["data"]
        else:
            return gatt_res, None

    @connect_required
    def write_cmd(self, uuid, data, conn_handle=None, attr_handle=None):
        if not conn_handle:
            conn_handle = self.conn_handle
        try:
            tx_complete = BLEEvtID.evt_tx_complete
        except Exception:
            tx_complete = BLEEvtID.gattc_evt_write_cmd_tx_complete
        if attr_handle is None:
            attr_handle = self.db_conns[conn_handle].get_char_value_handle(uuid)
        if attr_handle is None:
            raise NordicSemiException("Characteristic value handler not found")
        
        send_len=0
        data_len=len(data)
        while data_len > send_len:
            if data_len-send_len > self.db_conns[conn_handle].att_mtu-3:
                sub_len=self.db_conns[conn_handle].att_mtu-3
            else:
                sub_len=data_len-send_len
            sub_data=data[send_len:send_len+sub_len]
            write_params = BLEGattcWriteParams(
                BLEGattWriteOperation.write_cmd,
                BLEGattExecWriteFlag.unused,
                attr_handle,
                sub_data,
                0
            )

            # Send packet and skip waiting for TX-complete event. Try maximum 3 times.
            for _ in range(MAX_TRIES):
                try:
                    response = self.driver.ble_gattc_write(conn_handle, write_params)
                    logger.debug(
                        "Call ble_gattc_write: response({}) write_params({})".format(
                            response, write_params
                        )
                    )
                    break
                except NordicSemiException as e:
                    # Retry if NRF_ERROR_RESOURCES error code.
                    err = str(e)
                    if (("Error code: 19" in err) or ("NRF_ERROR_RESOURCES" in err) or
                        ("Error code: 12292" in err) or ("BLE_ERROR_NO_TX_PACKETS" in err)):
                        self.evt_sync[conn_handle].wait(evt=tx_complete, timeout=2)
                    else:
                        logger.debug("Unable to successfully call ble_gattc_write:"+err)
                        continue    
            send_len += sub_len

    @connect_required
    def authenticate(self,_role,conn_handle=None,bond=False,mitm=False,lesc=False,
                    keypress=False,io_caps=BLEGapIOCaps.none,oob=False,
                    min_key_size=7,max_key_size=16,enc_own=True,id_own=False,
                    sign_own=False,link_own=False,enc_peer=True,id_peer=False,
                    sign_peer=False,link_peer=False):
        if not conn_handle:
            conn_handle = self.conn_handle
        kdist_own = BLEGapSecKDist(enc=enc_own, id=id_own, sign=sign_own, link=link_own)
        kdist_peer = BLEGapSecKDist(
            enc=enc_peer, id=id_peer, sign=sign_peer, link=link_peer
        )
        sec_params = BLEGapSecParams(
            bond=bond,
            mitm=mitm,
            lesc=lesc,
            keypress=keypress,
            io_caps=io_caps,
            oob=oob,
            min_key_size=min_key_size,
            max_key_size=max_key_size,
            kdist_own=kdist_own,
            kdist_peer=kdist_peer,
        )

        self.driver.ble_gap_authenticate(conn_handle, sec_params)
        result = self.evt_sync[conn_handle].wait(evt=BLEEvtID.gap_evt_sec_params_request, timeout=10)
        # LE Secure Connections used only if both sides support it.
        if not sec_params.lesc or not result["peer_params"].lesc:
            # sd_ble_gap_sec_params_reply ... In the central role, sec_params must be set to NULL,
            # as the parameters have already been provided during a previous call to
            # sd_ble_gap_authenticate.
            sec_params = (
                None
                if self.db_conns[conn_handle].role == BLEGapRoles.central
                else sec_params
            )
            self.driver.ble_gap_sec_params_reply(
                conn_handle, BLEGapSecStatus.success, sec_params=sec_params, keyset=None
            )
        else:
            self.evt_sync[conn_handle].wait(evt=BLEEvtID.gap_evt_lesc_dhkey_request, timeout=5)

        result = self.evt_sync[conn_handle].wait(evt=BLEEvtID.gap_evt_auth_status)

        # TODO: The result returned is sometimes of a different type than
        # TODO: gap_evt_auth_status. This is a bug that needs further investigation.
        if "auth_status" not in result:
            return None

        # If success then keys are stored in self.driver._keyset.
        if result["auth_status"] == BLEGapSecStatus.success:
            self.db_conns[conn_handle]._keyset = BLEGapSecKeyset.from_c(
                self.driver._keyset
            )
        return result["auth_status"]

    @connect_required
    def encrypt(self, ediv, rand, ltk, conn_handle=None, auth=0, lesc=0, ltk_len=16):
        # @assert note that sd_ble_gap_encrypt results in
        # BLE_ERROR_INVALID_ROLE if not Central.
        if not conn_handle:
            conn_handle = self.conn_handle
        assert (
            self.db_conns[conn_handle].role == BLEGapRoles.central
        ), "Invalid role. Encryption can only be initiated by a Central Device."
        master_id = BLEGapMasterId(ediv=ediv, rand=rand)
        enc_info = BLEGapEncInfo(ltk=ltk, auth=auth, lesc=lesc, ltk_len=ltk_len)
        result = self.evt_sync[conn_handle].call(
            evt=BLEEvtID.gap_evt_conn_sec_update,
            func=self.driver.ble_gap_encrypt,
            conn_handle=conn_handle, 
            master_id=master_id, 
            enc_info=enc_info, 
            lesc=lesc
            )
        if result and "conn_sec" in result:
            return result["conn_sec"]
        else:
            return None

    # ...............................................................................................
    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        dict_data=dict(ble_driver=ble_driver, conn_handle=conn_handle, peer_addr=peer_addr,
                        rssi=rssi, adv_type=adv_type, adv_data=adv_data)
        self.scan_q.put(dict_data)
    
    
    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.db_conns[conn_handle] = Connection(peer_addr, role)
        self.evt_sync[conn_handle] = EvtSync(events=BLEEvtID)
        self.is_connected = True
        self.conn_handle = conn_handle

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        self.is_connected = False
        try:
            del self.db_conns[conn_handle]
        except KeyError:
            pass
        try:
            del self.evt_sync[conn_handle]
        except KeyError:
            pass

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        if src == BLEGapTimeoutSrc.conn:
            self.is_connected = False
        elif src == BLEGapTimeoutSrc.scan:
            self.is_scan_timeout=True

    def on_gap_evt_sec_params_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_sec_params_request, data=kwargs
        )

    def on_gap_evt_sec_info_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_sec_info_request, data=kwargs
        )

    def on_gap_evt_sec_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_sec_request, data=kwargs)

    def on_gap_evt_lesc_dhkey_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_lesc_dhkey_request, data=kwargs)

    def on_gap_evt_auth_status(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_auth_status, data=kwargs)

    def on_gap_evt_conn_sec_update(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_conn_sec_update, data=kwargs
        )

    def on_gap_evt_passkey_display(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_passkey_display, data=kwargs
        )

    def on_gap_evt_auth_key_request(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_auth_key_request, data=kwargs
        )

    def on_gap_evt_phy_update_request(self, ble_driver, conn_handle, peer_preferred_phys):
        peer_preferred_phys.tx_phys=driver.BLE_GAP_PHY_AUTO
        peer_preferred_phys.rx_phys=driver.BLE_GAP_PHY_AUTO
        try:
            ble_driver.ble_gap_phy_update(conn_handle, peer_preferred_phys)
        except NordicSemiException as ex:
            logger.error(f"Phy update failed. Exception: {ex}")

    def on_gap_evt_phy_update(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_phy_update, data=kwargs
        )

    def on_evt_tx_complete(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.evt_tx_complete, data=kwargs)

    def on_gattc_evt_write_cmd_tx_complete(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gattc_evt_write_cmd_tx_complete, data=kwargs
        )

    def on_gattc_evt_write_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gattc_evt_write_rsp, data=kwargs)

    def on_gap_evt_conn_param_update(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gap_evt_conn_param_update, data=kwargs
        )

    def on_gattc_evt_read_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gattc_evt_read_rsp, data=kwargs)

    def on_gattc_evt_prim_srvc_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gattc_evt_prim_srvc_disc_rsp, data=kwargs
        )

    def on_gattc_evt_char_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gattc_evt_char_disc_rsp, data=kwargs
        )

    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gattc_evt_desc_disc_rsp, data=kwargs
        )

    def on_gatts_evt_hvn_tx_complete(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gatts_evt_hvn_tx_complete, data=kwargs
        )

    def on_gatts_evt_hvc(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gatts_evt_hvc, data=kwargs)

    def on_gatts_evt_write(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gatts_evt_write, data=kwargs)

    def on_gap_evt_data_length_update_request(
        self, ble_driver, conn_handle, data_length_params
    ):
        try:
            self.driver.ble_gap_data_length_update(conn_handle, None, None)
        except NordicSemiException as ex:
            logger.error(f"Data length update failed. Exception: {ex}")

    def on_gap_evt_data_length_update(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(evt=BLEEvtID.gap_evt_data_length_update, data=kwargs)

    def on_gatts_evt_exchange_mtu_request(self, ble_driver, conn_handle, client_mtu):
        try:
            mtu_size=min(client_mtu,self.default_mtu)
            ble_driver.ble_gatts_exchange_mtu_reply(conn_handle, mtu_size)
        except NordicSemiException as ex:
            raise NordicSemiException(
                "MTU exchange reply failed. Common causes are: "
                "missing att_mtu setting in ble_cfg_set, "
                "different config tags used in ble_cfg_set and adv_start.") from ex

    def on_gatts_evt_sys_attr_missing(self, ble_driver, conn_handle, **kwargs):
        ble_driver.ble_gatts_sys_attr_set(conn_handle, None, 0, 0)

    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
        self.evt_sync[conn_handle].notify(
            evt=BLEEvtID.gattc_evt_exchange_mtu_rsp, data=kwargs
        )

    def on_rpc_log_entry(self, ble_driver, severity, message):
        logger.log(severity, message)

    def on_rpc_status(self, ble_driver, code, message):
        logger.debug("{}: {}".format(code, message))

    @wrapt.synchronized(observer_lock)
    def on_gap_evt_conn_param_update_request(
        self, ble_driver, conn_handle, conn_params
    ):
        for obs in self.observers:
            obs.on_conn_param_update_request(
                ble_adapter=self, conn_handle=conn_handle, conn_params=conn_params
            )

    @wrapt.synchronized(observer_lock)
    def on_gattc_evt_hvx(
        self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data
    ):
        if status != BLEGattStatusCode.success:
            logger.error(
                "Handle value notification failed. Status {}.".format(status)
            )
            return

        if hvx_type == BLEGattHVXType.notification:
            uuid = self.db_conns[conn_handle].get_char_uuid(attr_handle)
            if uuid is None:
                logger.info(f"Not able to look up UUID for attr_handle {attr_handle}")

            for obs in self.observers:
                obs.on_notification(self, conn_handle, uuid, data)
                obs.on_notification_handle(self, conn_handle, uuid, attr_handle, data)

        elif hvx_type == BLEGattHVXType.indication:
            uuid = self.db_conns[conn_handle].get_char_uuid(attr_handle)
            if uuid is None:
                logger.info(f"Not able to look up UUID for attr_handle {attr_handle}")

            for obs in self.observers:
                obs.on_indication(self, conn_handle, uuid, data)
                obs.on_indication_handle(self, conn_handle, uuid, attr_handle, data)

            self.driver.ble_gattc_hv_confirm(conn_handle, attr_handle)
