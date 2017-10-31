import time
import logging
from queue import Queue
from pc_ble_driver_py.ble_driver import *

logging.basicConfig()
log = logging.getLogger('test')
log.setLevel(logging.DEBUG)


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


def test_thingy(ble_tester):
    
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

    uuid = BLEUUIDBase([0x42, 0x00, 0x74, 0xA9,
                        0xFF, 0x52, 0x10, 0x9B,
                        0x33, 0x49, 0x35, 0x9B,
                        0x00, 0x00, 0x68, 0xEF][::-1])
    ble_tester.driver.ble_vs_uuid_add(uuid)
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
    ble_tester.adapter.enable_notification(conn_handle, BLEUUID(0x203, base=uuid))
    time.sleep(2)
    ble_tester.adapter.disable_notification(conn_handle, BLEUUID(0x203, base=uuid))
    res = ble_tester.adapter.read_req(conn_handle, BLEUUID(0x203, base=uuid))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = ble_tester.adapter.read_req(conn_handle, BLEUUID(0x201, base=uuid))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = ble_tester.adapter.read_req(conn_handle, BLEUUID(0x202, base=uuid))
    assert res[0] == BLEGattStatusCode.read_not_permitted
    res = ble_tester.adapter.read_req(conn_handle, BLEUUID(0x206, base=uuid))
    assert res[0] == BLEGattStatusCode.success
    ble_tester.adapter.write_req(conn_handle, BLEUUID(0x106, base=uuid), [22, 68, 134, 54])
    ble_tester.adapter.write_req(conn_handle, BLEUUID(0x106, base=uuid), [22]*200)
    ble_tester.adapter.enable_notification(conn_handle, BLEUUID(0x0504, base=uuid))
    time.sleep(1)
    ble_tester.adapter.disable_notification(conn_handle, BLEUUID(0x0504, base=uuid))
    ble_tester.disconnect(conn_handle)
