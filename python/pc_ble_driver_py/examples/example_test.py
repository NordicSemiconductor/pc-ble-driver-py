import logging
import time
from datetime import datetime


# TODO(vw): Fix. Hard code NRF51 for now
from pc_ble_driver_py import config
config.__conn_ic_id__ = 'NRF51'

from nrf_dll_load       import util
from pc_ble_driver_py.exceptions import NordicSemiException

from ble_device         import BLEDevice, BLEDeviceObserver
from gattc              import GattClient
from nrf_adapter        import NrfAdapter, NrfAdapterObserver
from nrf_event          import *
from nrf_event_sync     import EventSync
from nrf_types          import *
from observers          import GattClientObserver


def logger_setup():
    logger = logging.getLogger() #'fjase')
    logger.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logging.getLogger().addHandler(sh)
    return logger

logger = logger_setup()

class TestDevice(BLEDevice, BLEDeviceObserver, GattClientObserver):
    def __init__(self, driver, peer_addr):
        BLEDevice.__init__(self, driver, peer_addr)
        BLEDeviceObserver.__init__(self)
        GattClientObserver.__init__(self)

        self.observer_register(self)
        self.gattc.observer_register(self)

    def connect(self, timeout=2):
        logger.info('BLE: Connecting to %r', self.peer_addr)
        scan_params = self.driver.scan_params_setup()
        scan_params.timeout_s = timeout
        super(TestDevice, self).connect(scan_params=scan_params)
        if not self.connected.wait(timeout):
            raise NordicSemiException('Timeout. Device not found.')

    def pair(self):
        with EventSync(self.driver, [GapEvtSec]) as evt_sync:
            sec_params = self.driver.security_params_setup()
            sec_params.io_caps = GapIoCaps.KEYBOARD_DISPLAY
            self.gap_authenticate(sec_params)

            event = evt_sync.get(timeout=32)
            if not isinstance(event, GapEvtSecParamsRequest):
                raise NordicSemiException('Did not get GapEvtSecParamsRequest in time.')
            self.key_set = BLEGapSecKeyset()
            self.driver.ble_gap_sec_params_reply(self.conn_handle, BLEGapSecStatus.success, None, self.key_set)

            event = evt_sync.get(timeout=32)
            if not isinstance(event, GapEvtAuthKeyRequest):
                raise NordicSemiException('Did not get GapEvtConnSecUpdate in time.')
            if not event.key_type == GapAuthKeyType.PASSKEY:
                raise Exception("Unsupported auth key event")

            pass_key = raw_input("pass key: ")
            self.driver.ble_gap_auth_key_reply(self.conn_handle, event.key_type, map(ord, pass_key))

            event = evt_sync.get(timeout=32)
            if not isinstance(event, GapEvtConnSecUpdate):
                raise NordicSemiException('Did not get GapEvtConnSecUpdate in time.')
            event = evt_sync.get(timeout=32)
            if not isinstance(event, GapEvtAuthStatus):
                raise NordicSemiException('Did not get GapEvtConnSecUpdate in time.')

    def encrypt(self):
        ediv = self.key_set.sec_keyset.keys_peer.p_enc_key.master_id.ediv
        rand = util.uint8_array_to_list(self.key_set.sec_keyset.keys_peer.p_enc_key.master_id.rand, 8)
        ltk  = util.uint8_array_to_list(self.key_set.sec_keyset.keys_peer.p_enc_key.enc_info.ltk,
                            self.key_set.sec_keyset.keys_peer.p_enc_key.enc_info.ltk_len)
        lesc = self.key_set.sec_keyset.keys_peer.p_enc_key.enc_info.lesc
        auth = self.key_set.sec_keyset.keys_peer.p_enc_key.enc_info.auth

        with EventSync(self.driver, [GapEvtSec, GapEvtDisconnected]) as evt_sync:
            self.driver.ble_gap_encrypt(self.conn_handle, ediv, rand, ltk, lesc, auth)
            event = evt_sync.get(timeout=32)
            if   isinstance(event, GapEvtConnSecUpdate):
                logger.info("encrypted")
            elif isinstance(event, GapEvtDisconnected):
                raise NordicSemiException('Link disconnected')
            else:
                raise NordicSemiException('Got unexpected event %r' % event)

    def print_peer_db(self):
        proc_sync = self.gattc.primary_service_discovery()
        proc_sync.wait(8)
        if proc_sync.status != BLEGattStatusCode.success:
            print 'error'
            return

        services = proc_sync.result
        for service in services:
            proc_sync = self.gattc.characteristics_discovery(service)
            proc_sync.wait(8)
            if proc_sync.status != BLEGattStatusCode.success:
                print 'error'
                return

            for char in service.chars:
                read = self.gattc.read(char.handle_decl)
                if read is None:
                    print 'error'
                    return
                char.data_decl = read.data

                read = self.gattc.read(char.handle_value)
                if read is None:
                    print 'error'
                    return
                char.data_value = read.data

                proc_sync = self.gattc.descriptor_discovery(char)
                proc_sync.wait(8)
                if proc_sync.status != BLEGattStatusCode.success:
                    return
                for descr in char.descs:
                    read = self.gattc.read(descr.handle)
                    if read is None:
                        print 'error'
                        return
                    descr.data = read.data

        for service in services:
            logger.info(        '  0x%04x         0x%04x   -- %s', service.start_handle, service.srvc_uuid.get_value(), service.uuid)
            for char in service.chars:
                logger.info(    '    0x%04x       0x%04x   --   %r', char.handle_decl, char.char_uuid.get_value(), ''.join(map(chr, char.data_decl)))
                logger.info(    '      0x%04x     0x%04x   --     %r', char.handle_value, char.uuid.get_value(), ''.join(map(chr, char.data_value)))
                for descr in char.descs:
                    logger.info('      0x%04x     0x%04x   --     %r', descr.handle, descr.uuid.get_value(), ''.join(map(chr, descr.data)))

    def on_connection_param_update_request(self, device, event):
        logger.info("Request to update connection parameters")
        self.driver.ble_gap_conn_param_update(self.conn_handle, event.conn_params)

def scan(adapter, timeout=1):
    # Scan for devices
    class AdvObserver(NrfAdapterObserver):
        seen_devices = None

        def on_gap_evt_adv_report(self, adapter, event):
            #print repr(event)
            if self.seen_devices is None:
                self.seen_devices = dict()
            if self.seen_devices.has_key(str(event.peer_addr)):
                return
            self.seen_devices[str(event.peer_addr)] = event
            print event.peer_addr

    adv_observer = AdvObserver()
    adapter.observer_register(adv_observer)
    scan_params = adapter.driver.scan_params_setup()
    scan_params.timeout_s = timeout
    adapter.scan_start(scan_params)
    #adapter.scan_stop()
    # TODO: Wait for timeout event
    time.sleep(timeout)
    adapter.observer_unregister(adv_observer)


def run_test(adapter, peer_addr):
    # Connect and pair device
    device = TestDevice(adapter.driver, peer_addr)
    device.connect()
    #device.pair()
    device.print_peer_db()
    #time.sleep(8)

    #device.gattc.service_discovery()
    #time.sleep(1)

    ## Disconnect
    #device.disconnect()
    #time.sleep(2)

    ## Reconnect, reencrypt
    #device.connect()
    #device.encrypt()

    #print 'device name?', device.gattc.read(0x0003) # Normally name for NRF devices

def main(args):
    adapter = NrfAdapter.open_serial(serial_port=args.device, baud_rate=1000000)
    peer_addr = BLEGapAddr.from_string("D6:60:C4:A9:6B:5F,r")
    try:
        #scan(adapter, timeout=8)
        run_test(adapter, peer_addr)
    except:
        logger.exception("Exception during test run")
    finally:
        adapter.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog='example_test')
    parser.add_argument("-d", "--device", dest="device", required=True,     help="Select master device")
    #parser.add_argument("-f", "--family", dest="family", default='NRF51',   help="Choose IC family")
    args = parser.parse_args()

    main(args)
