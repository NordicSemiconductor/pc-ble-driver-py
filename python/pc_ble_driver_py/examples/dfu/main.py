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
import os
import Queue
import struct
import logging
import binascii

import sys
sys.path.append('../../')
# from nordicsemi.dfu.dfu_transport       import DfuTransport, DfuEvent

logger  = logging.getLogger(__name__)

class DFUAdapter(BLEAdapter):
    SERV_UUID   = 
    CP_UUID     = 
    DP_UUID     = 

    def __init__(self, target_device_name, target_device_addr, serial_port, baud_rate):
        super(DFUAdapter, self).__init__(serial_port, baud_rate)
        self.conn_handle        = None
        self.target_device_name = target_device_name
        self.target_device_addr = target_device_addr
        self.notifications_q    = Queue.Queue()

        self.ble_adapter.vs_uuid_add(DfuTransportBle.SERV_UUID)
        self.ble_gap_scan_start()
        self.ble_adapter.wait_for_event(BLEEvtID.gap_evt_connected)
        self.service_discovery(conn_handle=conn_handle)
        self.enable_notification(conn_handle=conn_handle, DFUAdapter.CP_UUID)


    def conn_params_setup(self):
        return BLEGapConnParams(min_conn_interval_ms = 15,
                                max_conn_interval_ms = 30,
                                conn_sup_timeout_ms  = 4000,
                                slave_latency        = 0)


    def write_control_point(self, data):
        handle          = self.db_conns[self.conn_handle].get_char_value_handle(DFUAdapter.CP_UUID)
        write_params    = BLEGattcWriteParams(BLEGattWriteOperation.write_req,
                                              BLEGattExecWriteFlag.prepared_cancel,
                                              handle,
                                              data,
                                              0)
        self.ble_gattc_write(self.conn_handle, write_params)


    def write_data_point(self, data):
        handle          = self.db_conns[self.conn_handle].get_char_value_handle(DFUAdapter.DP_UUID)
        write_params    = BLEGattcWriteParams(BLEGattWriteOperation.write_cmd,
                                              BLEGattExecWriteFlag.prepared_cancel,
                                              handle,
                                              data,
                                              0)
        self.ble_gattc_write(self.conn_handle, write_params)


    def on_gap_evt_connected(self, conn_handle, peer_addr, own_addr, role, conn_params):
        super(DFUAdapter, self).on_gap_evt_connected(conn_handle, peer_addr, own_addr, role, conn_params)
        self.conn_handle = conn_handle


    def on_gap_evt_adv_report(self, conn_handle, peer_addr, rssi, adv_type, adv_data):
        super(DFUAdapter, self).on_gap_evt_adv_report(conn_handle, peer_addr, rssi, adv_type, adv_data)

        dev_name_list = None
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]

        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        logger.debug('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                           dev_name))

        if (dev_name == self.target_device_name) or (address_string == self.target_device_addr):
            self.connect(peer_addr)


    def on_notification(self, conn_handle, uuid, data):
        if self.conn_handle     != conn_handle: return
        if DFUAdapter.CP_UUID   != uuid:        return
        self.notifications_q.put(data)



class DfuTransportBle(object):#(DfuTransport):

    DATA_PACKET_SIZE    = 20
    DEFAULT_TIMEOUT     = 20
    RETRIES_NUMBER      = 3

    OP_CODE = {
        'CreateObject'          : 0x01,
        'SetPRN'                : 0x02,
        'CalcChecSum'           : 0x03,
        'Execute'               : 0x04,
        'ReadObject'            : 0x05,
        'ReadObjectInfo'        : 0x06,
        'Response'              : 0x60,
    }

    RES_CODE = {
        'InvalidCode'           : 0x00,
        'Success'               : 0x01,
        'NotSupported'          : 0x02,
        'InvParam'              : 0x03,
        'InsufficientResources' : 0x04,
        'InvObject'             : 0x05,
        'InvSignature'          : 0x06,
        'UnsupportedType'       : 0x07,
        'OperationFailed'       : 0x0A,
    }

    def __init__(self, serial_port, target_device_name=None, target_device_addr=None, baud_rate=115200):
        super(DfuTransportBle, self).__init__()
        self.baud_rate          = baud_rate
        self.serial_port        = serial_port
        self.target_device_name = target_device_name
        self.target_device_addr = target_device_addr
        self.ble_adapter        = None


    def open(self):
        assert self.ble_adapter == None, 'BLE Adapter is already opened'

        super(DfuTransportBle, self).open()
        self.ble_adapter = DFUAdapter(target_device_name = self.target_device_name,
                                      target_device_addr = self.target_device_addr,
                                      serial_port        = self.serial_port,
                                      baud_rate          = self.baud_rate)



    def close(self):
        assert self.ble_adapter != None, 'BLE Adapter is already closed'
        super(DfuTransportBle, self).close()
        self.ble_adapter.close()
        self.ble_adapter = None


    def send_init_packet(self, init_packet):
        response = self._read_command_info()
        assert len(init_packet) <= response['max_size'], 'Init command is too long'

        for r in range(DfuTransportBle.RETRIES_NUMBER):
            try:
                self._create_command(len(init_packet))
                self._stream_data(data=init_packet)
                self._execute()
            except:
                pass
            break
        else:
            raise Exception("Failed to send init packet")


    def send_firmware(self, firmware):
        response    = self._read_data_info()
        object_size = response['max_size']

        crc = 0
        for i in range(0, len(firmware), object_size):
            data = firmware[i:i+object_size]
            for r in range(DfuTransportBle.RETRIES_NUMBER):
                try:
                    self._create_data(len(data))
                    crc = self._stream_data(data=data, crc=crc, offset=i)
                    self._execute()
                except:
                    pass
                break
            else:
                raise Exception("Failed to send firmware")
            self._send_event(event_type=DfuEvent.PROGRESS_EVENT, progress=len(data))


    def _create_command(self, size):
        self._create_object(0x01, size)


    def _create_data(self, size):
        self._create_object(0x02, size)


    def _create_object(self, object_type, size):
        self.ble_adapter.write_control_point([DfuTransportBle.OP_CODE['CreateObject'], object_type]\
                                            + map(ord, struct.pack('<L', size)))
        self._get_response(DfuTransportBle.OP_CODE['CreateObject'])


    def _calculate_checksum(self):
        self.ble_adapter.write_control_point([DfuTransportBle.OP_CODE['CalcChecSum']])
        response = self._get_response(DfuTransportBle.OP_CODE['CalcChecSum'])
        result   = dict()

        (result['offset'], result['crc']) = struct.unpack('<II', bytearray(response))
        return result


    def _execute(self):
        self.ble_adapter.write_control_point([DfuTransportBle.OP_CODE['Execute']])
        self._get_response(DfuTransportBle.OP_CODE['Execute'])


    def _read_command_info(self):
        return self._read_object_info(0x01)


    def _read_data_info(self):
        return self._read_object_info(0x02)


    def _read_object_info(self, request_type):
        self.ble_adapter.write_control_point([DfuTransportBle.OP_CODE['ReadObjectInfo'], request_type])
        response = self._get_response(DfuTransportBle.OP_CODE['ReadObjectInfo'])
        result   = dict()

        (result['max_size'], result['offset'], result['crc']) = struct.unpack('<III', bytearray(response))
        return result


    def _stream_data(self, data, crc=0, offset=0):
        for i in range(0, len(data), DfuTransportBle.DATA_PACKET_SIZE):
            to_transmit     = data[i:i + DfuTransportBle.DATA_PACKET_SIZE]
            self.ble_adapter.write_data_point(map(ord, to_transmit))
            crc     = binascii.crc32(to_transmit, crc) & 0xFFFFFFFF
            offset += len(to_transmit)

        response = self._calculate_checksum()
        if (crc != response['crc']):
            raise Exception('Failed CRC validation.\n'\
                          + 'Expected: {} Recieved: {}.'.format(crc, response['crc']))

        if (offset != response['offset']):
            raise Exception('Failed offset validation.\n'\
                          + 'Expected: {} Recieved: {}.'.format(offset, response['offset']))

        return crc


    def _get_response(self, operation):
        def get_dict_key(dictionary, value):
            return next((key for key, val in dictionary.items() if val == value), None)

        try:
            resp = self.ble_adapter.notifications_q.get(timeout=DfuTransportBle.DEFAULT_TIMEOUT)
        except Queue.Empty:
            raise Exception('Timeout: operation - {}'.format(get_dict_key(DfuTransportBle.OP_CODE,
                                                                          operation)))

        if resp[0] != DfuTransportBle.OP_CODE['Response']:
            raise Exception('No Response: 0x{:02X}'.format(resp[0]))

        if resp[1] != operation:
            raise Exception('Unexpected Executed OP_CODE.\n' \
                          + 'Expected: 0x{:02X} Received: 0x{:02X}'.format(operation, resp[1]))

        if resp[2] != DfuTransportBle.RES_CODE['Success']:
            raise Exception('Response Code {}'.format(get_dict_key(DfuTransportBle.RES_CODE, resp[2])))

        return resp[3:]


def main(serial_port):
    print('Serial port used: {}'.format(serial_port))
    dfu = DfuTransportBle(target_device_name='DfuTarg', serial_port=serial_port)
    dfu.open()
    dfu.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print('Enter Connectivity COM Port')
    quit()
