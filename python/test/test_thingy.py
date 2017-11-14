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

import time
import logging
import pytest
from queue import Queue
from pc_ble_driver_py.ble_driver import *

logging.basicConfig()
log = logging.getLogger('test')
log.setLevel(logging.DEBUG)

THINGY_UUID = BLEUUIDBase([0x42, 0x00, 0x74, 0xA9,
                           0xFF, 0x52, 0x10, 0x9B,
                           0x33, 0x49, 0x35, 0x9B,
                           0x00, 0x00, 0x68, 0xEF][::-1])


@pytest.fixture
def thingy_tester(ble_tester):
    ble_cfg = BLEConfigConnGatt()
    ble_cfg.att_mtu = 273
    ble_cfg.tag = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gatt, ble_cfg)

    cfg = BLEConfigCommon()
    cfg.vs_uuid_count = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.uuid_count, cfg)

    cfg = BLEConfigConnGattc()
    cfg.tag = 1
    cfg.write_cmd_tx_queue_size = 5
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gattc, cfg)

    cfg = BLEConfigGap()
    cfg.central_role_count = 0
    cfg.periph_role_count = 1
    cfg.central_sec_count = 0
    ble_tester.driver.ble_cfg_set(BLEConfig.role_count, cfg)

    cfg = BLEConfigGatts()
    cfg.service_changed = 0
    ble_tester.driver.ble_cfg_set(BLEConfig.service_changed, cfg)

    cfg = BLEConfigGatts()
    cfg.attr_tab_size = 1024
    ble_tester.driver.ble_cfg_set(BLEConfig.attr_tab_size, cfg)

    ble_tester.driver.ble_enable()

    ble_tester.driver.ble_vs_uuid_add(THINGY_UUID)
    scan_resp_q = Queue()
    ble_tester.start_scan(scan_resp_q)
    while True:
        peer_addr, name = scan_resp_q.get(timeout=5)
        if name == "Thingy":
            ble_tester.adapter.connect(peer_addr, tag=1)
            break
    conn_handle = ble_tester.conn_q.get(timeout=5)

    ble_tester.driver.ble_gattc_exchange_mtu_req(conn_handle, 273)
    ble_tester.events['mtu_exchanged_rsp'].wait()

    dlp = BLEGapDataLengthParams()
    dlp.max_rx_octets = 151
    dlp.max_tx_octets = 151
    dlp.max_rx_time_us = 0
    dlp.max_tx_time_us = 0
    dll = BLEGapDataLengthLimitation()
    try:
        ble_tester.driver.ble_gap_data_length_update(conn_handle, dlp, dll)
    except Exception:
        log.error(dll.tx_payload_limited_octets)
        log.error(dll.rx_payload_limited_octets)
        log.error(dll.tx_rx_time_limited_us)
        raise
    ble_tester.events['data_length_update'].wait()

    ble_tester.adapter.service_discovery(conn_handle)

    return ble_tester


def test_thingy_service_disc(ble_tester):
    ble_tester.driver.ble_enable()
    scan_rep_q = Queue()
    ble_tester.start_scan(scan_rep_q)
    while True:
        peer_addr, name = scan_rep_q.get(timeout=5)
        if name == "Thingy":
            ble_tester.adapter.connect(peer_addr, tag=0)
            break
    conn_handle = ble_tester.conn_q.get(timeout=5)
    log.error("Connected")
    log.error(conn_handle)
    ble_tester.adapter.service_discovery(conn_handle)
    ble_tester.disconnect()


def test_thingy_mtu(ble_tester):
    ble_cfg = BLEConfigConnGatt()
    ble_cfg.att_mtu = 273
    ble_cfg.tag = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gatt, ble_cfg)
    ble_tester.driver.ble_enable()
    scan_rep_q = Queue()
    ble_tester.start_scan(scan_rep_q)
    while True:
        peer_addr, name = scan_rep_q.get(timeout=5)
        if name == "Thingy":
            ble_tester.adapter.connect(peer_addr, tag=1)
            break
    conn_handle = ble_tester.conn_q.get(timeout=5)

    ble_tester.driver.ble_gattc_exchange_mtu_req(conn_handle, 273)
    time.sleep(1)
    ble_tester.driver.ble_gap_data_length_update(conn_handle, None, None)
    time.sleep(1)
    ble_tester.disconnect()


def thingy_uuid(uuid):
    return BLEUUID(uuid, base=THINGY_UUID)


def test_gattc_hvn(thingy_tester):
    conn_handle = 0
    thingy_tester.adapter.enable_notification(conn_handle, thingy_uuid(0x203))
    for _ in range(2):
        uuid, data = thingy_tester.notification_q.get(timeout=3)
        assert uuid.value == 0x203
        assert len(data) == 1
    thingy_tester.adapter.disable_notification(conn_handle, thingy_uuid(0x203))
    time.sleep(2)
    assert thingy_tester.notification_q.qsize() == 0


def test_gattc_read(thingy_tester):
    conn_handle = 0
    res = thingy_tester.adapter.read_req(conn_handle, thingy_uuid(0x203))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = thingy_tester.adapter.read_req(conn_handle, thingy_uuid(0x201))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = thingy_tester.adapter.read_req(conn_handle, thingy_uuid(0x202))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = thingy_tester.adapter.read_req(conn_handle, thingy_uuid(0x206))
    assert res[0] == BLEGattStatusCode.success


def test_gattc_write(thingy_tester):
    conn_handle = 0
    thingy_tester.adapter.write_req(conn_handle, thingy_uuid(0x106), [22, 68, 134, 54])
    thingy_tester.adapter.write_req(conn_handle, thingy_uuid(0x106), [22] * 200)
    thingy_tester.adapter.enable_notification(conn_handle, thingy_uuid(0x0504))
    time.sleep(1)
    thingy_tester.adapter.disable_notification(conn_handle, thingy_uuid(0x0504))
    thingy_tester.disconnect(conn_handle)
