import logging
from Queue          import Queue
from PCBLEDriver    import *

logger  = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class DbConnection(object):
    def __init__(self):
        self.services    = list()
        self.serv_disc_q = Queue()
        self.char_disc_q = Queue()
        self.desc_disc_q = Queue()


    def get_char_value_handle(self, uuid):
        for s in self.services:
            for c in s.chars:
                if c.uuid.value == uuid:
                    for d in c.descs:
                        if d.uuid.value == uuid:
                            return d.handle
        return None


    def get_cccd_handle(self, uuid):
        for s in self.services:
            for c in s.chars:
                if c.uuid.value == uuid:
                    for d in c.descs:
                        if d.uuid.value == BLEUUID.Standard.cccd:
                            return d.handle
        return None


    def get_char_handle(self, uuid):
        for s in self.services:
            for c in s.chars:
                if c.uuid.value == uuid:
                    return c.handle_decl
        return None


    def get_char_uuid(self, handle):
        for s in self.services:
            for c in s.chars:
                if (c.handle_decl <= handle) and (c.end_handle >= handle):
                    return c.uuid
                break



class BLEAdapterObserver(PCBLEObserver):
    def __init__(self, *args, **kwargs):
        super(BLEAdapterObserver, self).__init__(args, kwargs)


    def on_notification(self, context, conn_handle, uuid, data):
        pass



class BLEAdapter(PCBLEDriver, PCBLEObserver):
    def __init__(self, serial_port, baud_rate=115200):
        super(BLEAdapter, self).__init__(serial_port, baud_rate)
        self.conn_in_progress   = False
        self.db_conns           = dict()
        self.observer_register(self)


    def connect(self, address, scan_params=None, conn_params=None):
        if self.conn_in_progress:
            return
        self.ble_gap_connect(address=address, scan_params=scan_params, conn_params=conn_params)
        self.conn_in_progress = True


    def service_discovery(self, conn_handle, uuid=None):
        self.ble_gattc_prim_srvc_disc(conn_handle, uuid, 0x0001)

        while True:
            services = self.db_conns[conn_handle].serv_disc_q.get(timeout=5)
            if services:
                self.db_conns[conn_handle].services.extend(services)
            else:
                break

            if services[-1].end_handle == 0xFFFF:
                break
            else:
                self.ble_gattc_prim_srvc_disc(conn_handle, uuid, services[-1].end_handle + 1)

        for s in self.db_conns[conn_handle].services:
            self.ble_gattc_char_disc(conn_handle, s.start_handle, s.end_handle)
            while True:
                chars = self.db_conns[conn_handle].char_disc_q.get(timeout=5)
                if chars:
                    map(s.char_add, chars)
                else:
                    break

                self.ble_gattc_char_disc(conn_handle, chars[-1].handle_decl + 1, s.end_handle)

            for ch in s.chars:
                self.ble_gattc_desc_disc(conn_handle, ch.handle_value, ch.end_handle)
                while True:
                    descs = self.db_conns[conn_handle].desc_disc_q.get(timeout=5)
                    if descs:
                        ch.descs.extend(descs)
                    else:
                        break

                    if descs[-1].handle == ch.end_handle:
                        break
                    else:
                        self.ble_gattc_desc_disc(conn_handle, descs[-1].handle + 1, ch.end_handle)


    def enable_notification(self, conn_handle, uuid):
        cccd_list = [1, 0]
        handle = self.db_conns[conn_handle].get_cccd_handle(uuid)
        if handle == None:
            raise NordicSemiException('CCCD not found')

        write_params = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                           BLEGattExecWriteFlag.prepared_cancel,
                                           handle,
                                           cccd_list,
                                           0)

        self.ble_gattc_write(conn_handle, write_params)
        self.wait_for_event(evt = BLEEvtID.gattc_evt_write_rsp)


    def on_gap_evt_connected(self, context, conn_handle, peer_addr, own_addr, role, conn_params):
        self.db_conns[conn_handle]  = DbConnection()
        self.conn_in_progress       = False


    def on_gap_evt_disconnected(self, context, conn_handle, reason):
        del self.db_conns[conn_handle]


    def on_gap_evt_timeout(self, context, conn_handle, src):
        if src == BLEGapTimeoutSrc.conn:
            self.conn_in_progress = False


    def on_gattc_evt_prim_srvc_disc_rsp(self, context, conn_handle, status, services):
        if status == BLEGattStatusCode.attribute_not_found:
            self.db_conns[conn_handle].serv_disc_q.put(None)
            return

        elif status != BLEGattStatusCode.success:
            logger.error("Error. Primary services discovery failed. Status {}.".format(status))
            return
        self.db_conns[conn_handle].serv_disc_q.put(services)


    def on_gattc_evt_char_disc_rsp(self, context, conn_handle, status, characteristics):
        if status == BLEGattStatusCode.attribute_not_found:
            self.db_conns[conn_handle].char_disc_q.put(None)
            return

        elif status != BLEGattStatusCode.success:
            logger.error("Error. Characteristic discovery failed. Status {}.".format(status))
            return
        self.db_conns[conn_handle].char_disc_q.put(characteristics)


    def on_gattc_evt_desc_disc_rsp(self, context, conn_handle, status, descriptions):
        if status == BLEGattStatusCode.attribute_not_found:
            self.db_conns[conn_handle].desc_disc_q.put(None)
            return

        elif status != BLEGattStatusCode.success:
            logger.error("Error. Description discovery failed. Status {}.".format(status))
            return
        self.db_conns[conn_handle].desc_disc_q.put(descriptions)


    def on_gattc_evt_hvx(self, context, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        if status != BLEGattStatusCode.success:
            logger.error("Error. Description discovery failed. Status {}.".format(status))
            return

        if hvx_type == BLEGattHVXType.notification:
            uuid = self.db_conns[conn_handle].get_char_uuid(attr_handle)
            if uuid == None:
                raise NordicSemiException('UUID not found')

            for obs in self.observers:
                if issubclass(type(obs), BLEAdapterObserver):
                    obs.on_notification(self, conn_handle, uuid, data)