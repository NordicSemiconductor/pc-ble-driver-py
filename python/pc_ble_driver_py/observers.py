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



class BLEDriverObserver(object):
    def __init__(self, *args, **kwargs):
        super(BLEDriverObserver, self).__init__()
        pass


    def on_evt_data_length_changed(self, ble_driver, data_length_changed):
        pass


    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        pass


    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        pass


    def on_gap_evt_sec_params_request(self, ble_driver, conn_handle, peer_params):
        pass


    def on_gap_evt_sec_info_request(self, ble_driver, conn_handle, peer_addr, master_id, enc_info, id_info, sign_info):
        pass


    def on_gap_evt_sec_request(self, ble_driver, conn_handle, bond, mitm, lesc, keypress):
        pass


    def on_gap_evt_conn_param_update_request(self, ble_driver, conn_handle, conn_params):
        pass


    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        pass


    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        pass


    def on_gap_evt_auth_status(self, ble_driver, conn_handle, auth_status):
        pass


    def on_gap_evt_auth_key_request(self, ble_driver, conn_handle, key_type):
        pass


    def on_gap_evt_conn_sec_update(self, ble_driver, conn_handle):
        pass


    def on_evt_tx_complete(self, ble_driver, conn_handle, count):
        pass


    def on_gattc_evt_write_rsp(self, ble_driver, conn_handle, status, error_handle, attr_handle, write_op, offset, data):
        pass


    def on_gattc_evt_hvx(self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        pass


    def on_gattc_evt_read_rsp(self, ble_driver, conn_handle, status, error_handle, attr_handle, offset, data):
        pass


    def on_gattc_evt_prim_srvc_disc_rsp(self, ble_driver, conn_handle, status, services):
        pass


    def on_gattc_evt_char_disc_rsp(self, ble_driver, conn_handle, status, characteristics):
        pass


    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, status, descriptions):
        pass


    def on_gatts_evt_hvc(self, ble_driver, status, error_handle, attr_handle):
        pass


    def on_gatts_evt_write(self, ble_driver, conn_handle, attr_handle, uuid, op, auth_required, offset, length, data):
        pass


    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        pass

class BLEAdapterObserver(object):
    def __init__(self, *args, **kwargs):
        super(BLEAdapterObserver, self).__init__()


    def on_indication(self, ble_adapter, conn_handle, uuid, data):
        pass


    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        pass
        
        
    def on_conn_param_update_request(self, ble_adapter, conn_handle, conn_params):
        # Default behaviour is to accept connection parameter update
        ble_adapter.conn_param_update(conn_handle, conn_params)

