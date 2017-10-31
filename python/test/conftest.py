import pytest
import logging
import threading
from queue import Queue
from pc_ble_driver_py import config
config.__conn_ic_id__ = "NRF52"
from pc_ble_driver_py.ble_driver import *
from pc_ble_driver_py.ble_adapter import *
from pc_ble_driver_py.observers import *


logging.basicConfig()
log = logging.getLogger("pc-ble-driver-tester")
log.setLevel(logging.INFO)


@pytest.fixture
def ble_tester():
    _a = PcBLEDriverPyTester('COM76')
    _a.driver.open()
    yield _a
    _a.driver.close()


class PcBLEDriverPyTester(BLEDriverObserver, BLEAdapterObserver):
    """docstring for PcBLEDriverPyTester"""

    def __init__(self, serial_port):
        super(PcBLEDriverPyTester, self).__init__()
        self._adv_report_q = None
        self.conn_q = Queue()
        self.disconnected_evt = threading.Event()
        self.data_length_update_evt = threading.Event()
        self.mtu_exchanged_evt = threading.Event()
        self.driver = BLEDriver(serial_port=serial_port, auto_flash=False, baud_rate=1000000)
        self.adapter = BLEAdapter(self.driver)
        self.driver.observer_register(self)
        self.adapter.observer_register(self)
        self.events = dict(disconnected=threading.Event(),
                           data_length_update=threading.Event(),
                           mtu_exchanged=threading.Event(),
                           mtu_exchanged_rsp=threading.Event())

    def on_gap_evt_data_length_update(self, ble_driver, conn_handle, data_length_params):
        log.info("event: {}".format('on_evt_data_length_changed'))
        log.info("    max_tx_octets: {}".format(data_length_params.max_tx_octets))
        log.info("    max_rx_octets: {}".format(data_length_params.max_rx_octets))
        log.info("    max_tx_time_us: {}".format(data_length_params.max_tx_time_us))
        log.info("    max_rx_time_us: {}".format(data_length_params.max_rx_time_us))
        self.events['data_length_update'].set()

    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        log.info("event: {}, {}".format('on_gap_evt_connected', conn_handle))
        self.conn_q.put(conn_handle)

    def start_scan(self, queue):
        self._adv_report_q = queue
        self.driver.ble_gap_scan_start()

    def disconnect(self, conn_handle=0):
        self.events['disconnected'].clear()
        self.driver.ble_gap_disconnect(conn_handle)
        self.events['disconnected'].wait()
        self.events['disconnected'].clear()

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        log.info("event: {} (conn_handle: {})".format('on_gap_evt_disconnected', conn_handle))
        self.events['disconnected'].set()

    def on_gap_evt_sec_params_request(self, ble_driver, conn_handle, peer_params):
        log.debug("event: {}".format('on_gap_evt_sec_params_request'))

    def on_gap_evt_sec_info_request(self, ble_driver, conn_handle, peer_addr, master_id, enc_info, id_info, sign_info):
        log.debug("event: {}".format('on_gap_evt_sec_info_request'))

    def on_gap_evt_sec_request(self, ble_driver, conn_handle, bond, mitm, lesc, keypress):
        log.debug("event: {}".format('on_gap_evt_sec_request'))

    def on_gap_evt_conn_param_update_request(self, ble_driver, conn_handle, conn_params):
        log.debug("event: {}".format('on_gap_evt_conn_param_update_request'))

    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        log.debug("event: {}".format('on_gap_evt_timeout'))

    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        dev_name_list = None
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]

        else:
            return
        dev_name = "".join(chr(e) for e in dev_name_list)
        address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        log.info('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                       dev_name))
        if self._adv_report_q:
            self._adv_report_q.put((peer_addr, dev_name))

    def on_gap_evt_auth_status(self, ble_driver, conn_handle, auth_status):
        log.debug("event: {}".format('on_gap_evt_auth_status'))

    def on_gap_evt_auth_key_request(self, ble_driver, conn_handle, key_type):
        log.debug("event: {}".format('on_gap_evt_auth_key_request'))

    def on_gap_evt_conn_sec_update(self, ble_driver, conn_handle):
        log.debug("event: {}".format('on_gap_evt_conn_sec_update'))

    def on_gatts_evt_hvn_tx_complete(self, ble_driver, conn_handle, count):
        log.info("event: {}".format('on_gatts_evt_hvn_tx_complete'))

    def on_gattc_evt_write_cmd_tx_complete(self, ble_driver, conn_handle, count):
        log.info("event: {}".format('on_gattc_evt_write_cmd_tx_complete'))

    def on_gattc_evt_write_rsp(self, ble_driver, conn_handle, status, error_handle, attr_handle, write_op, offset, data):
        log.info("event: {}".format('on_gattc_evt_write_rsp'))

    def on_gattc_evt_hvx(self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        log.info("event: {}".format('on_gattc_evt_hvx'))

    def on_gattc_evt_read_rsp(self, ble_driver, conn_handle, status, error_handle, attr_handle, offset, data):
        log.info("event: {} {}".format('on_gattc_evt_read_rsp', data))

    def on_gattc_evt_prim_srvc_disc_rsp(self, ble_driver, conn_handle, status, services):
        log.info("event: {} services: {}".format('on_gattc_evt_prim_srvc_disc_rsp', [x.uuid.value for x in services]))

    def on_gattc_evt_char_disc_rsp(self, ble_driver, conn_handle, status, characteristics):
        log.info("event: {}".format('on_gattc_evt_char_disc_rsp'))

    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, status, descriptions):
        log.info("event: {}".format('on_gattc_evt_desc_disc_rsp'))

    def on_gatts_evt_hvc(self, ble_driver, status, error_handle, attr_handle):
        log.info("event: {}".format('on_gatts_evt_hvc'))

    def on_gatts_evt_write(self, ble_driver, conn_handle, attr_handle, uuid, op, auth_required, offset, length, data):
        log.info("event: {}".format('on_gatts_evt_write'))

    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        log.info("event: {}, att_mtu: {}".format('on_att_mtu_exchanged', att_mtu))
        self.events['mtu_exchanged'].set()

    def on_indication(self, ble_adapter, conn_handle, uuid, data):
        log.info("event: {} mtu: {}".format('on_indication', att_mtu))

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        log.info("event: {}, data: {}".format('on_notification', data))

    def on_conn_param_update_request(self, ble_adapter, conn_handle, conn_params):
        log.info("event: {}".format('on_conn_param_update_request'))
        # Default behaviour is to accept connection parameter update
        ble_adapter.conn_param_update(conn_handle, conn_params)

    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, status, att_mtu):
        log.info("event: {} att_mtu: {}".format('on_gattc_evt_exchange_mtu_rsp', att_mtu))
        self.events['mtu_exchanged_rsp'].set()
