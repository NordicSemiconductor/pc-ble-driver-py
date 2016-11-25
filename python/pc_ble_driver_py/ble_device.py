import logging
from threading          import Event

from ble_gattc          import GattClient
from nrf_event          import *
from nrf_event_sync     import EventSync

logger = logging.getLogger(__name__)


# TODO:
# * Implement interrupt driven pair, passkey and encrypt
# * Should we assert parameter types?
# * More events and commands needed

class BLEDeviceObserver(object):
    def on_connected(self, device, event):
        pass

    def on_disconnected(self, device, event):
        pass

    def on_connection_param_update_request(self, device, event):
        pass

    def on_connection_param_update(self, device, event):
        pass

    def on_sec_params_request(self, device, event):
        pass

    def on_auth_key_request(self, device, event):
        pass

    def on_conn_sec_update(self, device, event):
        pass

    def on_auth_status(self, device, event):
        pass


class BLEDevice(object):

    def __init__(self, driver, peer_addr):
        self.driver         = driver
        self.peer_addr      = peer_addr
        self.driver.observer_register(self)

        self.observers      = []
        self.connected      = Event()
        self.conn_handle    = None
        self.conn_params    = None
        self.own_addr       = None
        self.gattc          = None
        self.key_set        = None

    def connect(self, scan_params=None, conn_params=None):
        if scan_params is None:
            scan_params = self.driver.scan_params_setup()
        if conn_params is None:
            conn_params = self.driver.conn_params_setup()
        self.conn_params = conn_params
        self.driver.ble_gap_connect(self.peer_addr, conn_params=conn_params)

    def disconnect(self, hci_status_code=BLEHci.remote_user_terminated_connection):
        with EventSync(self.driver, GapEvtDisconnected) as evt_sync:
            self.driver.ble_gap_disconnect(self.conn_handle, hci_status_code)
            event = evt_sync.get(self.conn_params.conn_sup_timeout_ms / 1000.)

    def observer_register(self, observer):
        self.observers.append(observer)

    def observer_unregister(self, observer):
        self.observers.remove(observer)

    def gap_authenticate(self, sec_params):
        self.driver.ble_gap_authenticate(self.conn_handle, sec_params)

    def on_event(self, nrf_driver, event):
        #logger.info("event %r", event)
        if   isinstance(event, GapEvtConnected):
            if event.peer_addr != self.peer_addr:
                return # Filter out events for other links
            self.conn_handle    = event.conn_handle
            self.own_addr       = event.own_addr
            self.gattc          = GattClient(self.driver, self.conn_handle)

            for obs in self.observers[:]:
                obs.on_connected(self, event)

            self.connected.set()
        elif isinstance(event, GapEvtTimeout):
            if event.src == BLEGapTimeoutSrc.conn:
                #self.connected.clear()
                pass
        elif event.conn_handle != self.conn_handle:
            return # Filter out events for other links
        elif isinstance(event, GapEvtDisconnected):
            self.connected.clear()

            for obs in self.observers[:]:
                obs.on_disconnected(self, event)

            self.conn_handle    = None
            self.own_addr       = None
            self.gattc          = None
        elif isinstance(event, GapEvtConnParamUpdateRequest):
            for obs in self.observers[:]:
                obs.on_connection_param_update_request(self, event)
        elif isinstance(event, GapEvtConnParamUpdate):
            for obs in self.observers[:]:
                obs.on_connection_param_update(self, event)
        elif isinstance(event, GapEvtSecParamsRequest):
            for obs in self.observers[:]:
                obs.on_sec_params_request(self, event)
        elif isinstance(event, GapEvtAuthKeyRequest):
            for obs in self.observers[:]:
                obs.on_auth_key_request(self, event)
        elif isinstance(event, GapEvtConnSecUpdate):
            for obs in self.observers[:]:
                obs.on_conn_sec_update(self, event)
        elif isinstance(event, GapEvtAuthStatus):
            for obs in self.observers[:]:
                obs.on_auth_status(self, event)
