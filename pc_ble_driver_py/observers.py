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

import logging

logger = logging.getLogger(__name__)


def gen_conn_params_str(conn_params):
    conn_params_str = "\n"
    conn_params_str += "  min_conn_interval_ms({})\n".format(
        conn_params.min_conn_interval_ms
    )
    conn_params_str += "  max_conn_interval_ms({})\n".format(
        conn_params.max_conn_interval_ms
    )
    conn_params_str += "  slave_latency({})".format(conn_params.slave_latency)
    return conn_params_str


def get_addr_str(addr):
    return ":".join("{:02X}".format(a) for a in addr.addr)


class BLEDriverObserver(object):
    def __init__(self, *args, **kwargs):
        super(BLEDriverObserver, self).__init__()
        pass

    def on_gap_evt_data_length_update(
        self, ble_driver, conn_handle, data_length_params
    ):
        pass

    def on_gap_evt_data_length_update_request(
        self, ble_driver, conn_handle, data_length_params
    ):
        pass

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        logger.debug(
            "evt> connected conn({})\n peer_addr({})\n role({})\n conn_params({})".format(
                conn_handle,
                get_addr_str(peer_addr),
                role,
                gen_conn_params_str(conn_params),
            )
        )

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        logger.debug(
            "evt> disconnected conn({})\n reason({})".format(conn_handle, reason)
        )

    def on_gap_evt_sec_params_request(self, ble_driver, conn_handle, peer_params):
        logger.debug(
            "evt> sec_params_request conn({})\n peer_params({})".format(
                conn_handle, peer_params
            )
        )

    def on_gap_evt_sec_info_request(
        self,
        ble_driver,
        conn_handle,
        peer_addr,
        master_id,
        enc_info,
        id_info,
        sign_info,
    ):
        logger.debug(
            "evt> sec_info_request conn({})\n peer_addr({})\n master_id({})\n"
            " enc_info({})\n id_info({})\n sign_info({})".format(
                conn_handle,
                get_addr_str(peer_addr),
                master_id,
                enc_info,
                id_info,
                sign_info,
            )
        )

    def on_gap_evt_sec_request(
        self, ble_driver, conn_handle, bond, mitm, lesc, keypress
    ):
        logger.debug(
            "evt> sec_request conn({})\n bond({})\n mitm({})\n lesc({})\n keypress({})".format(
                conn_handle, bond, mitm, lesc, keypress
            )
        )

    def on_gap_evt_passkey_display(
        self, ble_driver, conn_handle, passkey):
        logger.debug(
            "evt> passkey_display conn({}) passkey({})\n".format(
                conn_handle, passkey
            )
        )

    def on_gap_evt_conn_param_update_request(
        self, ble_driver, conn_handle, conn_params
    ):
        logger.debug(
            "evt> conn_param_update_request conn({})\n conn_params({})".format(
                conn_handle, gen_conn_params_str(conn_params)
            )
        )

    def on_gap_evt_conn_param_update(self, ble_driver, conn_handle, conn_params):
        pass

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        logger.debug("evt> timeout conn({})\n src({})".format(conn_handle, src))

    def on_gap_evt_adv_report(
        self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data
    ):
        logger.debug(
            "evt> adv_report conn({})\n peer_addr({})\n rssi({})\n adv_type({})".format(
                conn_handle, get_addr_str(peer_addr), rssi, adv_type
            )
        )

    def on_gap_evt_auth_status(
        self,
        ble_driver,
        conn_handle,
        error_src,
        bonded,
        sm1_levels,
        sm2_levels,
        kdist_own,
        kdist_peer,
        auth_status,
    ):
        logger.debug(
            "evt> auth_status conn({})\n error_src({})\n bonded({})\n sm1_levels({})\n"
            " sm2_levels({})\n kdist_own({})\n kdist_peer({})\n auth_status({})".format(
                conn_handle,
                error_src,
                bonded,
                sm1_levels,
                sm2_levels,
                kdist_own,
                kdist_peer,
                auth_status,
            )
        )

    def on_gap_evt_auth_key_request(self, ble_driver, conn_handle, key_type):
        logger.debug(
            "evt> auth_key_request conn({})\n key_type({})".format(
                conn_handle, key_type
            )
        )

    def on_gap_evt_conn_sec_update(self, ble_driver, conn_handle, conn_sec):
        logger.debug(
            "evt> conn_sec_update conn({})\n conn_sec({})".format(conn_handle, conn_sec)
        )

    def on_gap_evt_rssi_changed(self, ble_driver, conn_handle, rssi):
        logger.debug("evt> rssi_changed conn(%d)\n rssi(%d)", conn_handle, rssi)

    def on_evt_tx_complete(self, ble_driver, conn_handle, count):
        logger.debug("evt> tx_complete conn({})\n count({})".format(conn_handle, count))

    def on_gattc_evt_write_cmd_tx_complete(self, ble_driver, conn_handle, count):
        logger.debug(f"evt> gattc_evt_write_cmd_tx_complete conn({conn_handle})\n count({count})")

    def on_gattc_evt_write_rsp(
        self,
        ble_driver,
        conn_handle,
        status,
        error_handle,
        attr_handle,
        write_op,
        offset,
        data,
    ):
        logger.debug(
            "evt> on_gattc_evt_write_rsp conn({})\n status({})\n error_handle({})\n"
            " attr_handle({})\n write_op({})\n offset({})\n data({})".format(
                conn_handle, status, error_handle, attr_handle, write_op, offset, data
            )
        )

    def on_gattc_evt_hvx(
        self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data
    ):
        logger.debug(
            "evt> on_gattc_evt_hvx status({}) conn({})\n error_handle({})\n attr_handle({})\n"
            " hvx_type({})\n data({})".format(
                status, conn_handle, error_handle, attr_handle, hvx_type, data
            )
        )

    def on_gattc_evt_read_rsp(
        self, ble_driver, conn_handle, status, error_handle, attr_handle, offset, data
    ):
        logger.debug(
            "evt> on_gattc_evt_read_rsp status({}) conn({})\n error_handle({})\n"
            " attr_handle({})\n offset({})\n data({})".format(
                status, conn_handle, error_handle, attr_handle, offset, data
            )
        )

    def on_gattc_evt_prim_srvc_disc_rsp(
        self, ble_driver, conn_handle, status, services
    ):
        services_str = "\n ".join(str(s) for s in services)
        logger.debug(
            "evt> on_gattc_evt_prim_srvc_disc_rsp status({}) conn({})\n {}".format(
                status, conn_handle, services_str
            )
        )

    def on_gattc_evt_char_disc_rsp(
        self, ble_driver, conn_handle, status, characteristics
    ):
        chars_str = "\n ".join(str(c) for c in characteristics)
        logger.debug(
            "evt> on_gattc_evt_char_disc_rsp status({}) conn({})\n {}".format(
                status, conn_handle, chars_str
            )
        )

    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, status, descriptors):
        descs_str = "\n ".join(str(d) for d in descriptors)
        logger.debug(
            "evt> on_gattc_evt_desc_disc_rsp status({}) conn({})\n {}".format(
                status, conn_handle, descs_str
            )
        )

    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, status, att_mtu):
        logger.debug(
            "evt> on_gattc_evt_exchange_mtu_rsp conn({}) status({}) server_mtu({})".format(
                conn_handle, status, att_mtu
            )
        )

    def on_gatts_evt_hvn_tx_complete(self, ble_driver, conn_handle, count):
        pass

    def on_gatts_evt_hvc(self, ble_driver, conn_handle, attr_handle):
        logger.debug(
            "evt> on_gatts_evt_hvc conn({})\n attr_handle({})".format(
                conn_handle, attr_handle
            )
        )

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
        logger.debug(
            "evt> on_gatts_evt_write conn({})\n attr_handle({})\n uuid({})\n"
            " op({})\n auth_required({})\n offset({})\n length({})\n data({})".format(
                conn_handle, attr_handle, uuid, op, auth_required, offset, length, data
            )
        )

    def on_gatts_evt_sys_attr_missing(
        self,
        ble_driver,
        conn_handle,
        hint
    ):
        logger.debug(
            f"evt> on_gatts_evt_sys_attr_missing conn({conn_handle}) hint({hint})"
        )

    def on_gatts_evt_exchange_mtu_request(self, ble_driver, conn_handle, client_mtu):
        logger.debug(
            f"evt> on_gatts_evt_exchange_mtu_request conn({conn_handle}) client_mtu({client_mtu})"
        )

    def on_rpc_status(self, ble_driver, code, message):
        logger.debug("evt> status code({}) message({})".format(code, message))

    def on_rpc_log_entry(self, ble_driver, severity, message):
        logger.debug("evt> severity({}) message({})".format(severity, message))

    def on_gap_evt_phy_update_request(self, ble_driver, conn_handle, peer_preferred_phys):
        logger.debug(
            "evt> on_gap_evt_phy_update_request conn({})\n peer_preferred_phys({}) ".format(
                conn_handle, peer_preferred_phys
            )
        )

    def on_gap_evt_phy_update(self, ble_driver, conn_handle, status, tx_phy, rx_phy):
        logger.debug(
            "evt> on_gap_evt_phy_update conn({})\n status({})\n"
            "tx_phy({})\n rx_phy({})".format(
                conn_handle, status, tx_phy, rx_phy
            )
        )


class BLEAdapterObserver(object):
    """
    Observer used by BLEAdapter
    """

    def __init__(self, *args, **kwargs):
        super(BLEAdapterObserver, self).__init__()

    def on_indication(self, ble_adapter, conn_handle, uuid, data):
        pass

    def on_indication_handle(self, ble_adapter, conn_handle, uuid, attr_handle, data):
        pass

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        pass

    def on_notification_handle(self, ble_adapter, conn_handle, uuid, attr_handle, data):
        pass

    def on_conn_param_update_request(self, ble_adapter, conn_handle, conn_params):
        logger.debug(
            "evt> conn_param_update_request conn({})\n conn_params({})".format(
                conn_handle, gen_conn_params_str(conn_params)
            )
        )
