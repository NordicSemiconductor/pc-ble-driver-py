import time
import logging
from queue import Queue
from pc_ble_driver_py.ble_driver import *

logging.basicConfig()
log = logging.getLogger('test')
log.setLevel(logging.DEBUG)


def test_uuid_count(ble_tester):
    ble_cfg = BLEConfigCommon()
    ble_cfg.vs_uuid_count = 3
    ble_tester.driver.ble_cfg_set(BLEConfig.uuid_count, ble_cfg)
    ble_tester.driver.ble_enable()
    for i in range(3):
        base = [i, 0x01, 0x02, 0x03, 0x04, 0x05, 0x10, 0x00,
                0x80, 0x00, 0x00, 0x80, 0x5F, 0x9B, 0x34, 0xFB]
        vs_uuid = BLEUUIDBase(base)
        ble_tester.driver.ble_vs_uuid_add(vs_uuid)
    base[0] = 5
    vs_uuid = BLEUUIDBase(base)
    try:
        ble_tester.driver.ble_vs_uuid_add(vs_uuid)
    except NordicSemiException:
        pass
    else:
        raise AssertionError("Not raised")


def test_cfg_conn_gattc(ble_tester):
    cfg = BLEConfigConnGattc()
    cfg.conn_cfg_tag = 1
    cfg.write_cmd_tx_queue_size = 5
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gattc, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_conn_gatts(ble_tester):
    cfg = BLEConfigConnGatts()
    cfg.conn_cfg_tag = 1
    cfg.hvn_tx_queue_size = 5
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gattc, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_conn_gap(ble_tester):
    cfg = BLEConfigConnGap()
    cfg.conn_cfg_tag = 1
    cfg.conn_count = 2
    cfg.event_length = 40
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gap, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_conn_l2cap(ble_tester):
    cfg = BLEConfigConnL2cap()
    cfg.conn_cfg_tag = 1
    cfg.ch_count = 23
    cfg.rx_mps = 30
    cfg.rx_queue_size = 2
    cfg.tx_mps = 30
    cfg.tx_queue_size = 2
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_l2cap, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_uuid(ble_tester):
    cfg = BLEConfigCommon()
    cfg.vs_uuid_count = 5
    ble_tester.driver.ble_cfg_set(BLEConfig.uuid_count, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_device_name(ble_tester):
    cfg = BLEConfigGap()
    cfg.device_name = "test123"
    cfg.device_name_read_only = False
    ble_tester.driver.ble_cfg_set(BLEConfig.device_name, cfg)
    ble_tester.driver.ble_enable()
    ble_tester.driver.ble_gap_adv_start()
    time.sleep(10)


def test_cfg_role_count(ble_tester):
    cfg = BLEConfigGap()
    cfg.central_role_count = 1
    cfg.periph_role_count = 1
    cfg.central_sec_count = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.role_count, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_service_changed(ble_tester):
    cfg = BLEConfigGatts()
    cfg.service_changed = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.service_changed, cfg)
    ble_tester.driver.ble_enable()


def test_cfg_attr_tab_size(ble_tester):
    cfg = BLEConfigGatts()
    cfg.attr_tab_size = 1804
    ble_tester.driver.ble_cfg_set(BLEConfig.attr_tab_size, cfg)
    ble_tester.driver.ble_enable()


def test_adv_start(ble_tester):
    ble_cfg = BLEConfigConnGatt()
    ble_cfg.att_mtu = 273
    ble_cfg.tag = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.conn_gatt, ble_cfg)

    cfg = BLEConfigGap()
    cfg.device_name = "test123"
    cfg.device_name_read_only = False
    ble_tester.driver.ble_cfg_set(BLEConfig.device_name, cfg)

    cfg = BLEConfigGatts()
    cfg.service_changed = 1
    ble_tester.driver.ble_cfg_set(BLEConfig.service_changed, cfg)
    adv_data = BLEAdvData(complete_local_name='test123')
    ble_tester.driver.ble_enable()
    ble_tester.driver.ble_gap_adv_data_set(adv_data)
    ble_tester.driver.ble_gap_adv_start(tag=1)
    time.sleep(2)
