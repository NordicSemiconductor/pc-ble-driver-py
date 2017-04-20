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

import argparse
import sys
import time
import Queue
import logging
import traceback

from pc_ble_driver_py.nrf_observers         import NrfAdapterObserver, GattClientObserver
from pc_ble_driver_py.exceptions            import NordicSemiException

def logger_setup():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(sh)
    return logger


def init(conn_ic_id):
    global logger, config, nrf_types, nrf_event, NrfAdapter, GattClient, EventSync
    logger = logger_setup()

    from pc_ble_driver_py import config
    config.set_conn_ic(conn_ic_id)

    from pc_ble_driver_py                   import nrf_types
    from pc_ble_driver_py                   import nrf_event
    from pc_ble_driver_py.nrf_adapter       import NrfAdapter
    from pc_ble_driver_py.gattc             import GattClient
    from pc_ble_driver_py.nrf_event_sync    import EventSync

class HRCollector(NrfAdapterObserver, GattClientObserver):
    def __init__(self, adapter):
        super(HRCollector, self).__init__()
        self.adapter        = adapter
        self.gattc          = None
        self.hr_handle      = None
        self.hr_cccd        = None
        self.scan_active    = False
        self.adapter.observer_register(self)

    def scan_and_connect(self, target_dev_name):
        event = None
        with EventSync(self.adapter, nrf_event.GapEvtAdvReport) as evt_sync:
            scan_params = self.adapter.driver.scan_params_setup()
            scan_params.timeout_s = 10
            self.adapter.scan_start(scan_params)

            print("Scanning for device, press ctrl-c to stop")
            self.scan_active = True
            while self.scan_active:
                event = evt_sync.get(timeout=.1)
                if event is None:
                    continue

                dev_name = event.getDeviceName()
                print('AdvReport address: {}, device_name: {}'.format(event.peer_addr, dev_name))

                if (dev_name == target_dev_name):
                    break

        if event is None:
            raise NordicSemiException('Timeout, unable find device.')

        self.gattc  = GattClient(self.adapter.driver, event.peer_addr)
        proc_sync   = self.gattc.connect().wait(8)

        if not proc_sync.status:
            raise NordicSemiException('Timeout, unable to connect to device.')

        self.gattc.observer_register(self)

        if config.sd_api_ver_get() >= 3:
            att_mtu = self.adapter.att_mtu_exchange(self.device.conn_handle)

    def start_hr_collect(self):
        print("Discovering peer database")
        services = self.gattc.get_peer_db()

        if not services:
            print("Peer database discovery failed")
            return

        self.print_peer_db(services)

        for service in services:
            for char in service.chars:
                if not char.uuid.get_value() == nrf_types.BLEUUID.Standard.heart_rate.value:
                    continue
                self.hr_handle = char.handle_value
                for descr in char.descs:
                    if descr.uuid.get_value() == nrf_types.BLEUUID.Standard.cccd.value:
                        self.hr_cccd = descr.handle

        if None in [self.hr_handle, self.hr_cccd]:
            raise NordicSemiException("No heart rate service found")
        self.gattc.enable_notification(self.hr_cccd)

    def print_peer_db(self, services):
        def repr_val(data):
            if data is None:
                return '(no value)'
            return repr(''.join(map(chr, data)))
        def uuid_string(uuid):
            if uuid.base.def_base:
                return '0x{:04x}'.format(uuid.get_value())
            else:
                return '0x{}'.format(''.join(['{:02X}'.format(i) for i in uuid.as_array()]))
        def char_property_string(char_props):
            properties = []
            if char_props.broadcast:
                properties.append('BROADCAST')
            if char_props.read:
                properties.append('READ')
            if char_props.write_wo_resp:
                properties.append('WRITE_WO_R')
            if char_props.write:
                properties.append('WRITE')
            if char_props.notify:
                properties.append('NOTIFY')
            if char_props.indicate:
                properties.append('INDICATE')
            if char_props.auth_signed_wr:
                properties.append('AUTH_SW')
            #    properties.append('EXT_PROP')
            return 'properties: ' + ' '.join(properties)

        for service in services:
            print(        '  0x{:04x}        {}  {}'.format(    service.start_handle, uuid_string(service.srvc_uuid), service.uuid))
            for char in service.chars:
                val = repr_val(char.data_decl)
                val_pad = ' '*max(0, 50-len(val))
                print(    '    0x{:04x}      {}    {}{}{}'.format(  char.handle_decl, uuid_string(char.char_uuid), val, val_pad , char_property_string(char.char_props)))
                print(    '      0x{:04x}    {}      {}'.format(char.handle_value, uuid_string(char.uuid), repr_val(char.data_value)))
                for descr in char.descs:
                    print('      0x{:04x}    {}      {}'.format(descr.handle, uuid_string(descr.uuid), repr_val(descr.data)))


    def parse_hr(self, event):
        MASK_HR_VALUE_16BIT           = 1 << 0
        MASK_SENSOR_CONTACT_DETECTED  = 1 << 1
        MASK_SENSOR_CONTACT_SUPPORTED = 1 << 2
        MASK_EXPENDED_ENERGY_INCLUDED = 1 << 3
        MASK_RR_INTERVAL_INCLUDED     = 1 << 4

        flag = event.data[0]

        i = 1
        status = []
        if (flag & MASK_HR_VALUE_16BIT) == MASK_HR_VALUE_16BIT:
            status.append('two byte hr')
            hr = (event.data[i+1] << 8) + event.data[i]
            i += 2
        else:
            hr = event.data[1]
            i += 1

        if (flag & MASK_SENSOR_CONTACT_SUPPORTED) == MASK_SENSOR_CONTACT_SUPPORTED:
            status.append('contact sensor supported')
        if (flag & MASK_SENSOR_CONTACT_DETECTED) == MASK_SENSOR_CONTACT_DETECTED:
            status.append('contact detected')

        rr_values = []
        if (flag & MASK_RR_INTERVAL_INCLUDED) == MASK_RR_INTERVAL_INCLUDED:
            status.append('RR intervale included: ')
            while i+1 < len(event.data):
                rr_values.append(str((event.data[i+1] << 8) + event.data[i]))
                i += 2

        print('hr {:5} status {}{}'.format(hr, ', '.join(status), ', '.join(rr_values)))

    def on_notification(self, gatt_client, event):
        if event.attr_handle == self.hr_handle:
            self.parse_hr(event)
        else:
            print('Connection: {}, {} = {}'.format(event.conn_handle, event.attr_handle, event.data))

    def on_gap_evt_timeout(self, adapter, event):
        self.scan_active = False

    #def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
    #    print('ATT MTU exchanged: conn_handle={} att_mtu={}'.format(conn_handle, att_mtu))


    #def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
    #    print('ATT MTU exchange response: conn_handle={}'.format(conn_handle))


def main(serial_port, baud_rate, target_dev_name):
    print('Serial port used: {}'.format(serial_port))
    ble_enable_params = nrf_types.BLEEnableParams(
            vs_uuid_count       = 1, service_changed    = False,
            periph_conn_count   = 0, central_conn_count = 1,
            central_sec_count   = 1)

    if config.sd_api_ver_get() >= 3:
        print("Enabling larger ATT MTUs")
        ble_enable_params.att_mtu = 50

    adapter = None
    try:
        adapter   = NrfAdapter.open_serial(serial_port, baud_rate, ble_enable_params)
        collector = HRCollector(adapter)
        collector.scan_and_connect(target_dev_name)
        collector.start_hr_collect()

        time.sleep(10)
    except KeyboardInterrupt:
        pass
    if adapter:
        print("Closing")
        adapter.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Example heart rate collector.')
    parser.add_argument('--family',         dest='family',  required=True,          help='Connectivity IC identifier (NRF51, NRF52)')
    parser.add_argument('-p', '--port',     dest='port',    required=True,          help='Connectivity IC com port')
    parser.add_argument('-b', '--baudrate', dest='baud',    default=None, type=int, help='Connectivity IC com port baud rate')
    parser.add_argument('-n', '--name',     dest='name',    default="Nordic_HRM",   help='Device name to connect to')

    args = parser.parse_args()

    init(args.family)
    main(args.port, args.baud, args.name)
