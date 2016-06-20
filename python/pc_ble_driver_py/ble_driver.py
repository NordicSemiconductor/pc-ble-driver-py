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
import traceback
from enum       import Enum
from functools  import wraps
from types      import NoneType
from wrapt      import synchronized
from threading  import Lock

import sys
import ctypes
import os
import platform
import imp
import importlib

logger  = logging.getLogger(__name__)
logging.basicConfig()

logger.setLevel(logging.DEBUG)

# Load pc_ble_driver

SWIG_MODULE_NAME = "pc_ble_driver"
SHLIB_NAME = "pc_ble_driver_shared"

this_dir, this_file = os.path.split(__file__)

if sys.maxsize > 2**32:
    shlib_arch = 'x86_64'
else:
    shlib_arch = 'x86_32'

shlib_prefix = ""
if sys.platform.lower().startswith('win'):
    shlib_plat = 'win'
    shlib_postfix = ".dll"
elif sys.platform.lower().startswith('linux'):
    shlib_plat = 'linux'
    shlib_prefix = "lib"
    shlib_postfix = ".so"
elif sys.platform.startswith('dar'):
    shlib_plat = 'osx'
    shlib_prefix = "lib"
    shlib_postfix = ".dylib"
    # OS X uses a single library for both archs
    shlib_arch = ""

shlib_file = '{}{}{}'.format(shlib_prefix, SHLIB_NAME, shlib_postfix)
shlib_dir = os.path.join(os.path.abspath(this_dir), 'lib', shlib_plat, shlib_arch)
shlib_path = os.path.join(shlib_dir, shlib_file)

if not os.path.exists(shlib_path):
    raise RuntimeError('Failed to locate the pc_ble_driver shared library: {}.'.format(shlib_path))

try:
    _shlib = ctypes.cdll.LoadLibrary(shlib_path)
except Exception as error:
    raise RuntimeError("Could not load shared library {} : '{}'.".format(shlib_path, error))

logger.info('Shared library folder: {}'.format(shlib_dir))

sys.path.append(shlib_dir)
import pc_ble_driver as driver
import ble_driver_types as util

class NordicSemiException(Exception):
    """
    Exception used as based exception for other exceptions defined in this package.
    """
    pass



def NordicSemiErrorCheck(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        err_code = func(*args, **kwargs)
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException('Failed to {}. Error code: {}'.format(func.__name__, err_code))

    return wrapper



class BLEEvtID(Enum):
    gap_evt_connected               = driver.BLE_GAP_EVT_CONNECTED
    gap_evt_disconnected            = driver.BLE_GAP_EVT_DISCONNECTED
    gap_evt_adv_report              = driver.BLE_GAP_EVT_ADV_REPORT
    gap_evt_timeout                 = driver.BLE_GAP_EVT_TIMEOUT
    evt_tx_complete                 = driver.BLE_EVT_TX_COMPLETE
    gattc_evt_write_rsp             = driver.BLE_GATTC_EVT_WRITE_RSP
    gattc_evt_hvx                   = driver.BLE_GATTC_EVT_HVX
    gattc_evt_prim_srvc_disc_rsp    = driver.BLE_GATTC_EVT_PRIM_SRVC_DISC_RSP
    gattc_evt_char_disc_rsp         = driver.BLE_GATTC_EVT_CHAR_DISC_RSP
    gattc_evt_desc_disc_rsp         = driver.BLE_GATTC_EVT_DESC_DISC_RSP



class BLEEnableParams(object):
    def __init__(self,
                 vs_uuid_count,
                 service_changed,
                 periph_conn_count,
                 central_conn_count,
                 central_sec_count,
                 attr_tab_size = driver.BLE_GATTS_ATTR_TAB_SIZE_DEFAULT):
        self.vs_uuid_count      = vs_uuid_count
        self.attr_tab_size      = attr_tab_size
        self.service_changed    = service_changed
        self.periph_conn_count  = periph_conn_count
        self.central_conn_count = central_conn_count
        self.central_sec_count  = central_sec_count


    def to_c(self):
        ble_enable_params                                       = driver.ble_enable_params_t()
        ble_enable_params.common_enable_params.p_conn_bw_counts = None
        ble_enable_params.common_enable_params.vs_uuid_count    = self.vs_uuid_count
        ble_enable_params.gatts_enable_params.attr_tab_size     = self.attr_tab_size
        ble_enable_params.gatts_enable_params.service_changed   = self.service_changed
        ble_enable_params.gap_enable_params.periph_conn_count   = self.periph_conn_count
        ble_enable_params.gap_enable_params.central_conn_count  = self.central_conn_count
        ble_enable_params.gap_enable_params.central_sec_count   = self.central_sec_count

        return ble_enable_params



class BLEGapAdvType(Enum):
    connectable_undirected      = driver.BLE_GAP_ADV_TYPE_ADV_IND
    connectable_directed        = driver.BLE_GAP_ADV_TYPE_ADV_DIRECT_IND
    scanable_undirected         = driver.BLE_GAP_ADV_TYPE_ADV_SCAN_IND
    non_connectable_undirected  = driver.BLE_GAP_ADV_TYPE_ADV_NONCONN_IND



class BLEGapRoles(Enum):
    invalid = driver.BLE_GAP_ROLE_INVALID
    periph  = driver.BLE_GAP_ROLE_PERIPH
    central = driver.BLE_GAP_ROLE_CENTRAL



class BLEGapTimeoutSrc(Enum):
    advertising     = driver.BLE_GAP_TIMEOUT_SRC_ADVERTISING
    securitu_req    = driver.BLE_GAP_TIMEOUT_SRC_SECURITY_REQUEST
    scan            = driver.BLE_GAP_TIMEOUT_SRC_SCAN
    conn            = driver.BLE_GAP_TIMEOUT_SRC_CONN



class BLEGapAdvParams(object):
    def __init__(self, interval_ms, timeout_s):
        self.interval_ms    = interval_ms
        self.timeout_s      = timeout_s


    def to_c(self):
        adv_params              = driver.ble_gap_adv_params_t()
        adv_params.type         = BLEGapAdvType.connectable_undirected.value
        adv_params.p_peer_addr  = None  # Undirected advertisement.
        adv_params.fp           = driver.BLE_GAP_ADV_FP_ANY
        adv_params.p_whitelist  = None
        adv_params.interval     = util.msec_to_units(self.interval_ms,
                                                                util.UNIT_0_625_MS)
        adv_params.timeout      = self.timeout_s

        return adv_params



class BLEGapScanParams(object):
    def __init__(self, interval_ms, window_ms, timeout_s):
        self.interval_ms    = interval_ms
        self.window_ms      = window_ms
        self.timeout_s      = timeout_s


    def to_c(self):
        scan_params             = driver.ble_gap_scan_params_t()
        scan_params.active      = True
        scan_params.selective   = False
        scan_params.p_whitelist = None
        scan_params.interval    = util.msec_to_units(self.interval_ms,
                                                                util.UNIT_0_625_MS)
        scan_params.window      = util.msec_to_units(self.window_ms,
                                                                util.UNIT_0_625_MS)
        scan_params.timeout     = self.timeout_s

        return scan_params



class BLEGapConnParams(object):
    def __init__(self, min_conn_interval_ms, max_conn_interval_ms, conn_sup_timeout_ms, slave_latency):
        self.min_conn_interval_ms   = min_conn_interval_ms
        self.max_conn_interval_ms   = max_conn_interval_ms
        self.conn_sup_timeout_ms    = conn_sup_timeout_ms
        self.slave_latency          = slave_latency


    @classmethod
    def from_c(cls, conn_params):
        return cls(min_conn_interval_ms = util.units_to_msec(conn_params.min_conn_interval,
                                                             util.UNIT_1_25_MS),
                   max_conn_interval_ms = util.units_to_msec(conn_params.max_conn_interval,
                                                             util.UNIT_1_25_MS),
                   conn_sup_timeout_ms  = util.units_to_msec(conn_params.conn_sup_timeout,
                                                             util.UNIT_10_MS),
                   slave_latency        = conn_params.slave_latency)


    def to_c(self):
        conn_params                    = driver.ble_gap_conn_params_t()
        conn_params.min_conn_interval  = util.msec_to_units(self.min_conn_interval_ms,
                                                            util.UNIT_1_25_MS)
        conn_params.max_conn_interval  = util.msec_to_units(self.max_conn_interval_ms,
                                                            util.UNIT_1_25_MS)
        conn_params.conn_sup_timeout   = util.msec_to_units(self.conn_sup_timeout_ms,
                                                            util.UNIT_10_MS)
        conn_params.slave_latency      = self.slave_latency

        return conn_params



class BLEGapAddr(object):
    class Types(Enum):
        public                          = driver.BLE_GAP_ADDR_TYPE_PUBLIC
        random_static                   = driver.BLE_GAP_ADDR_TYPE_RANDOM_STATIC
        random_private_resolvable       = driver.BLE_GAP_ADDR_TYPE_RANDOM_PRIVATE_RESOLVABLE
        random_private_non_resolvable   = driver.BLE_GAP_ADDR_TYPE_RANDOM_PRIVATE_NON_RESOLVABLE


    def __init__(self, addr_type, addr):
        assert isinstance(addr_type, BLEGapAddr.Types), 'Invalid argument type'
        self.addr_type  = addr_type
        self.addr       = addr


    @classmethod
    def from_c(cls, addr):
        return cls(addr_type    = BLEGapAddr.Types(addr.addr_type),
                   addr         = util.uint8_array_to_list(addr.addr, driver.BLE_GAP_ADDR_LEN))


    def to_c(self):
        addr_array      = util.list_to_uint8_array(self.addr)
        addr            = driver.ble_gap_addr_t()
        addr.addr_type  = self.addr_type.value
        addr.addr       = addr_array.cast()
        return addr



class BLEAdvData(object):
    class Types(Enum):
        flags                               = driver.BLE_GAP_AD_TYPE_FLAGS
        service_16bit_uuid_more_available   = driver.BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_MORE_AVAILABLE
        service_16bit_uuid_complete         = driver.BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_COMPLETE
        service_32bit_uuid_more_available   = driver.BLE_GAP_AD_TYPE_32BIT_SERVICE_UUID_MORE_AVAILABLE
        service_32bit_uuid_complete         = driver.BLE_GAP_AD_TYPE_32BIT_SERVICE_UUID_COMPLETE
        service_128bit_uuid_more_available  = driver.BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_MORE_AVAILABLE
        service_128bit_uuid_complete        = driver.BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_COMPLETE
        short_local_name                    = driver.BLE_GAP_AD_TYPE_SHORT_LOCAL_NAME
        complete_local_name                 = driver.BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME
        tx_power_level                      = driver.BLE_GAP_AD_TYPE_TX_POWER_LEVEL
        class_of_device                     = driver.BLE_GAP_AD_TYPE_CLASS_OF_DEVICE
        simple_pairing_hash_c               = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_HASH_C
        simple_pairing_randimizer_r         = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_RANDOMIZER_R
        security_manager_tk_value           = driver.BLE_GAP_AD_TYPE_SECURITY_MANAGER_TK_VALUE
        security_manager_oob_flags          = driver.BLE_GAP_AD_TYPE_SECURITY_MANAGER_OOB_FLAGS
        slave_connection_interval_range     = driver.BLE_GAP_AD_TYPE_SLAVE_CONNECTION_INTERVAL_RANGE
        solicited_sevice_uuids_16bit        = driver.BLE_GAP_AD_TYPE_SOLICITED_SERVICE_UUIDS_16BIT
        solicited_sevice_uuids_128bit       = driver.BLE_GAP_AD_TYPE_SOLICITED_SERVICE_UUIDS_128BIT
        service_data                        = driver.BLE_GAP_AD_TYPE_SERVICE_DATA
        public_target_address               = driver.BLE_GAP_AD_TYPE_PUBLIC_TARGET_ADDRESS
        random_target_address               = driver.BLE_GAP_AD_TYPE_RANDOM_TARGET_ADDRESS
        appearance                          = driver.BLE_GAP_AD_TYPE_APPEARANCE
        advertising_interval                = driver.BLE_GAP_AD_TYPE_ADVERTISING_INTERVAL
        le_bluetooth_device_address         = driver.BLE_GAP_AD_TYPE_LE_BLUETOOTH_DEVICE_ADDRESS
        le_role                             = driver.BLE_GAP_AD_TYPE_LE_ROLE
        simple_pairng_hash_c256             = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_HASH_C256
        simple_pairng_randomizer_r256       = driver.BLE_GAP_AD_TYPE_SIMPLE_PAIRING_RANDOMIZER_R256
        service_data_32bit_uuid             = driver.BLE_GAP_AD_TYPE_SERVICE_DATA_32BIT_UUID
        service_data_128bit_uuid            = driver.BLE_GAP_AD_TYPE_SERVICE_DATA_128BIT_UUID
        uri                                 = driver.BLE_GAP_AD_TYPE_URI
        information_3d_data                 = driver.BLE_GAP_AD_TYPE_3D_INFORMATION_DATA
        manufacturer_specific_data          = driver.BLE_GAP_AD_TYPE_MANUFACTURER_SPECIFIC_DATA



    def __init__(self, **kwargs):
        self.records = dict()
        for k in kwargs:
            self.records[BLEAdvData.Types[k]] = kwargs[k]


    def to_c(self):
        data_list = list()
        for k in self.records:
            data_list.append(len(self.records[k]) + 1) # add type length
            data_list.append(k.value)
            if isinstance(self.records[k], str):
                data_list.extend([ord(c) for c in self.records[k]])

            elif isinstance(self.records[k], list):
                data_list.extend(self.records[k])

            else:
                raise NordicSemiException('Unsupported value type: 0x{:02X}'.format(type(self.records[k])))

        data_len = len(data_list)
        if data_len == 0:
            return (data_len, None)
        else:
            self.__data_array  = util.list_to_uint8_array(data_list)
            return (data_len, self.__data_array.cast())


    @classmethod
    def from_c(cls, adv_report_evt):
        ad_list         = util.uint8_array_to_list(adv_report_evt.data, adv_report_evt.dlen)
        ble_adv_data    = cls()
        index           = 0
        while index < len(ad_list):
            ad_len  = ad_list[index]
            if ad_len == 0:
                break
            ad_type = ad_list[index + 1]
            offset  = index + 2
            try:
                key                         = BLEAdvData.Types(ad_type)
                ble_adv_data.records[key]   = ad_list[offset: offset + ad_len - 1]
            except ValueError:
                logger.error('Invalid advertising data type: 0x{:02X}'.format(ad_type))
                pass
            except IndexError:
                logger.error('Invalid advertising data: {}'.format(ad_list))
                return ble_adv_data
            index += (ad_len + 1)

        return ble_adv_data



class BLEGattWriteOperation(Enum):
    invalid             = driver.BLE_GATT_OP_INVALID
    write_req           = driver.BLE_GATT_OP_WRITE_REQ
    write_cmd           = driver.BLE_GATT_OP_WRITE_CMD
    singed_write_cmd    = driver.BLE_GATT_OP_SIGN_WRITE_CMD
    prepare_write_req   = driver.BLE_GATT_OP_PREP_WRITE_REQ
    execute_write_req   = driver.BLE_GATT_OP_EXEC_WRITE_REQ



class BLEGattHVXType(Enum):
    invalid         = driver.BLE_GATT_HVX_INVALID
    notification    = driver.BLE_GATT_HVX_NOTIFICATION
    indication      = driver.BLE_GATT_HVX_INDICATION



class BLEGattStatusCode(Enum):
    success             = driver.BLE_GATT_STATUS_SUCCESS
    attribute_not_found = driver.BLE_GATT_STATUS_ATTERR_ATTRIBUTE_NOT_FOUND


class BLEGattExecWriteFlag(Enum):
    prepared_cancel = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_CANCEL
    prepared_write  = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_WRITE



class BLEGattcWriteParams(object):
    def __init__(self, write_op, flags, handle, data, offset):
        assert isinstance(write_op, BLEGattWriteOperation), 'Invalid argument type'
        assert isinstance(flags, BLEGattExecWriteFlag),     'Invalid argument type'
        self.write_op   = write_op
        self.flags      = flags
        self.handle     = handle
        self.data       = data
        self.offset     = offset


    @classmethod
    def from_c(cls, gattc_write_params):
        return cls(write_op = BLEGattWriteOperation(gattc_write_params.write_op),
                   flags    = gattc_write_params.flags,
                   handle   = gattc_write_params.handle,
                   data     = util.uint8_array_to_list(gattc_write_params.p_value,
                                                       gattc_write_params.len))


    def to_c(self):
        self.__data_array       = util.list_to_uint8_array(self.data) #TODO memory leak in C
        write_params            = driver.ble_gattc_write_params_t()
        write_params.p_value    = self.__data_array.cast()
        write_params.flags      = self.flags.value
        write_params.handle     = self.handle
        write_params.offset     = self.offset
        write_params.len        = len(self.data)
        write_params.write_op   = self.write_op.value

        return write_params


class BLEHci(Enum):
    success                                     = driver.BLE_HCI_STATUS_CODE_SUCCESS
    unknown_btle_command                        = driver.BLE_HCI_STATUS_CODE_UNKNOWN_BTLE_COMMAND
    unknown_connection_identifier               = driver.BLE_HCI_STATUS_CODE_UNKNOWN_CONNECTION_IDENTIFIER
    authentication_failure                      = driver.BLE_HCI_AUTHENTICATION_FAILURE
    pin_or_key_missing                          = driver.BLE_HCI_STATUS_CODE_PIN_OR_KEY_MISSING
    memory_capacity_exceeded                    = driver.BLE_HCI_MEMORY_CAPACITY_EXCEEDED
    connection_timeout                          = driver.BLE_HCI_CONNECTION_TIMEOUT
    command_disallowed                          = driver.BLE_HCI_STATUS_CODE_COMMAND_DISALLOWED
    invalid_btle_command_parameters             = driver.BLE_HCI_STATUS_CODE_INVALID_BTLE_COMMAND_PARAMETERS
    remote_user_terminated_connection           = driver.BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION
    remote_dev_termination_due_to_low_resources = driver.BLE_HCI_REMOTE_DEV_TERMINATION_DUE_TO_LOW_RESOURCES
    remote_dev_termination_due_to_power_off     = driver.BLE_HCI_REMOTE_DEV_TERMINATION_DUE_TO_POWER_OFF
    local_host_terminated_connection            = driver.BLE_HCI_LOCAL_HOST_TERMINATED_CONNECTION
    unsupported_remote_feature                  = driver.BLE_HCI_UNSUPPORTED_REMOTE_FEATURE
    invalid_lmp_parameters                      = driver.BLE_HCI_STATUS_CODE_INVALID_LMP_PARAMETERS
    unspecified_error                           = driver.BLE_HCI_STATUS_CODE_UNSPECIFIED_ERROR
    lmp_response_timeout                        = driver.BLE_HCI_STATUS_CODE_LMP_RESPONSE_TIMEOUT
    lmp_pdu_not_allowed                         = driver.BLE_HCI_STATUS_CODE_LMP_PDU_NOT_ALLOWED
    instant_passed                              = driver.BLE_HCI_INSTANT_PASSED
    pairintg_with_unit_key_unsupported          = driver.BLE_HCI_PAIRING_WITH_UNIT_KEY_UNSUPPORTED
    differen_transaction_collision              = driver.BLE_HCI_DIFFERENT_TRANSACTION_COLLISION
    controller_busy                             = driver.BLE_HCI_CONTROLLER_BUSY
    conn_interval_unacceptable                  = driver.BLE_HCI_CONN_INTERVAL_UNACCEPTABLE
    directed_advertiser_timeout                 = driver.BLE_HCI_DIRECTED_ADVERTISER_TIMEOUT
    conn_terminated_due_to_mic_failure          = driver.BLE_HCI_CONN_TERMINATED_DUE_TO_MIC_FAILURE
    conn_failed_to_be_established               = driver.BLE_HCI_CONN_FAILED_TO_BE_ESTABLISHED



class BLEUUID(object):
    class Standard(Enum):
        unknown             = 0x0000
        service_primary     = 0x2800
        service_secondary   = 0x2801
        cccd                = 0x2902
        battery_level       = 0x2A19
        heart_rate          = 0x2A37


    def __init__(self, value):
        self.type   = driver.BLE_UUID_TYPE_BLE # can be overwrite by BLEDriver.ble_vs_uuid_add()

        if isinstance(value, BLEUUID.Standard):
            self.value  = value
        else:
            try:
                self.value  = BLEUUID.Standard(value)
            except(ValueError):
                self.value  = value


    def __str__(self):
        if isinstance(self.value, BLEUUID.Standard):
            return '0x{:02X} ({})'.format(self.value.value, self.value)
        else:
            return '0x{:02X}'.format(self.value)


    @classmethod
    def uuid_from_c(cls, uuid):
        return cls(value = uuid.uuid)


    def uuid128_to_c(self):
        if not isinstance(self.value, list):
            raise NordicSemiException('Not vendor specific UUID {}'.format(self.value))

        lsb_list                = list(reversed(self.value))
        self.__uuid128_array    = util.list_to_uint8_array(lsb_list)
        uuid                    = driver.ble_uuid128_t()
        uuid.uuid128            = self.__uuid128_array.cast()
        return uuid


    def uuid_to_c(self):
        uuid        = driver.ble_uuid_t()
        uuid.uuid   = self.value
        uuid.type   = self.type
        return uuid



class BLEDescriptor(object):
    def __init__(self, uuid, handle):
        logger.debug('New descriptor uuid: {}, handle: {}'.format(uuid, handle))
        self.handle = handle
        self.uuid   = uuid


    @classmethod
    def from_c(cls, gattc_desc):
        return cls(uuid     = BLEUUID.uuid_from_c(gattc_desc.uuid),
                   handle   = gattc_desc.handle)



class BLECharacteristic(object):
    def __init__(self, uuid, handle_decl, handle_value):
        logger.debug('New characteristic uuid: {}, declaration handle: {}, value handle: {}'.format(uuid, handle_decl, handle_value))
        self.uuid           = uuid
        self.handle_decl    = handle_decl
        self.handle_value   = handle_value
        self.end_handle     = None
        self.descs          = list()


    @classmethod
    def from_c(cls, gattc_char):
        return cls(uuid         = BLEUUID.uuid_from_c(gattc_char.uuid),
                   handle_decl  = gattc_char.handle_decl,
                   handle_value = gattc_char.handle_value)



class BLEService(object):
    def __init__(self, uuid, start_handle, end_handle):
        logger.debug('New service uuid: {}, start handle: {}, end handle: {}'.format(uuid, start_handle, end_handle))
        self.uuid           = uuid
        self.start_handle   = start_handle
        self.end_handle     = end_handle
        self.chars          = list()


    @classmethod
    def from_c(cls, gattc_service):
        return cls(uuid         = BLEUUID.uuid_from_c(gattc_service.uuid),
                   start_handle = gattc_service.handle_range.start_handle,
                   end_handle   = gattc_service.handle_range.end_handle)


    def char_add(self, char):
        char.end_handle = self.end_handle
        self.chars.append(char)
        if len(self.chars) > 1:
            self.chars[-2].end_handle = char.handle_decl - 1


class SerialPortDescriptor(object):
    def __init__(self, port = "", manufacturer = "", serial_number = "", pnp_id = "", location_id = "", vendor_id = "", product_id = ""):
        self.port = port
        self.manufacturer = manufacturer
        self.serial_number = serial_number
        self.pnp_id = pnp_id
        self.location_id = location_id
        self.vendor_id = vendor_id
        self.product_id = product_id
    
    @classmethod
    def to_string(cls, char_arr):
        s = util.char_array_to_list(char_arr, driver.SD_RPC_MAXPATHLEN)
        for i, c in enumerate(s):
            if c == '\x00':
                break
        s = s[0:i]
        s = ''.join(s)
        return s

    @classmethod
    def from_c(cls, org):
        return cls(port = org.port,
                   manufacturer = org.manufacturer,
                   serial_number = org.serialNumber,
                   pnp_id = org.pnpId,
                   location_id = org.locationId,
                   vendor_id = org.vendorId,
                   product_id = org.productId)

class BLEDriverObserver(object):
    def __init__(self, *args, **kwargs):
        super(BLEDriverObserver, self).__init__()
        pass


    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, own_addr, role, conn_params):
        pass


    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        pass


    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        pass


    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        pass


    def on_evt_tx_complete(self, ble_driver, conn_handle, count):
        pass


    def on_gattc_evt_write_rsp(self, ble_driver, conn_handle, status, error_handle, attr_handle, write_op, offset, data):
        pass


    def on_gattc_evt_hvx(self, ble_driver, conn_handle, status, error_handle, attr_handle, hvx_type, data):
        pass


    def on_gattc_evt_prim_srvc_disc_rsp(self, ble_driver, conn_handle, status, services):
        pass


    def on_gattc_evt_char_disc_rsp(self, ble_driver, conn_handle, status, characteristics):
        pass


    def on_gattc_evt_desc_disc_rsp(self, ble_driver, conn_handle, status, descriptions):
        pass



class BLEDriver(object):
    observer_lock   = Lock()
    api_lock        = Lock()
    def __init__(self, serial_port, baud_rate=115200):
        super(BLEDriver, self).__init__()
        self.observers      = list()
        phy_layer           = driver.sd_rpc_physical_layer_create_uart(serial_port,
                                                                       baud_rate,
                                                                       driver.SD_RPC_FLOW_CONTROL_NONE,
                                                                       driver.SD_RPC_PARITY_NONE);
        link_layer          = driver.sd_rpc_data_link_layer_create_bt_three_wire(phy_layer, 100)
        transport_layer     = driver.sd_rpc_transport_layer_create(link_layer, 100)
        self.rpc_adapter    = driver.sd_rpc_adapter_create(transport_layer)


    @synchronized(api_lock)
    @classmethod
    def enum_serial_ports(cls):
        MAX_SERIAL_PORTS = 64
        c_descs = [ driver.sd_rpc_serial_port_desc_t() for i in range(MAX_SERIAL_PORTS)]
        c_desc_arr = util.list_to_serial_port_desc_array(c_descs)

        arr_len = driver.new_uint32()
        driver.uint32_assign(arr_len, MAX_SERIAL_PORTS)

        err_code = driver.sd_rpc_serial_port_enum(c_desc_arr, arr_len)
        if err_code != driver.NRF_SUCCESS:
            raise NordicSemiException('Failed to {}. Error code: {}'.format(func.__name__, err_code))

        dlen = driver.uint32_value(arr_len)

        descs   = util.serial_port_desc_array_to_list(c_desc_arr, dlen)
        return map(SerialPortDescriptor.from_c, descs)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def open(self):
        return driver.sd_rpc_open(self.rpc_adapter,
                                  self.status_handler,
                                  self.ble_evt_handler,
                                  self.log_message_handler)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def close(self):
        return driver.sd_rpc_close(self.rpc_adapter)


    @synchronized(observer_lock)
    def observer_register(self, observer):
        self.observers.append(observer)


    @synchronized(observer_lock)
    def observer_unregister(self, observer):
        self.observers.remove(observer)


    def ble_enable_params_setup(self):
        return BLEEnableParams(vs_uuid_count      = 1,
                               service_changed    = False,
                               periph_conn_count  = 1,
                               central_conn_count = 1,
                               central_sec_count  = 1)


    def adv_params_setup(self):
        return BLEGapAdvParams(interval_ms = 40,
                               timeout_s   = 180)


    def scan_params_setup(self):
        return BLEGapScanParams(interval_ms = 200,
                                window_ms   = 150,
                                timeout_s   = 10)


    def conn_params_setup(self):
        return BLEGapConnParams(min_conn_interval_ms = 15,
                                max_conn_interval_ms = 30,
                                conn_sup_timeout_ms  = 4000,
                                slave_latency        = 0)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_enable(self, ble_enable_params=None):
        if not ble_enable_params:
            ble_enable_params = self.ble_enable_params_setup()
        assert isinstance(ble_enable_params, BLEEnableParams), 'Invalid argument type'
        return driver.sd_ble_enable(self.rpc_adapter, ble_enable_params.to_c(), None)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_adv_start(self, adv_params=None):
        if not adv_params:
            adv_params = self.adv_params_setup()
        assert isinstance(adv_params, BLEGapAdvParams), 'Invalid argument type'
        return driver.sd_ble_gap_adv_start(self.rpc_adapter, adv_params.to_c())


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_adv_stop(self):
        return driver.sd_ble_gap_adv_stop()


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_scan_start(self, scan_params=None):
        if not scan_params:
            scan_params = self.scan_params_setup()
        assert isinstance(scan_params, BLEGapScanParams), 'Invalid argument type'
        return driver.sd_ble_gap_scan_start(self.rpc_adapter, scan_params.to_c())


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_scan_stop(self):
        return driver.sd_ble_gap_scan_stop()


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_connect(self, address, scan_params=None, conn_params=None):
        assert isinstance(address, BLEGapAddr), 'Invalid argument type'

        if not scan_params:
            scan_params = self.scan_params_setup()
        assert isinstance(scan_params, BLEGapScanParams), 'Invalid argument type'

        if not conn_params:
            conn_params = self.conn_params_setup()
        assert isinstance(conn_params, BLEGapConnParams), 'Invalid argument type'

        return driver.sd_ble_gap_connect(self.rpc_adapter, 
                                                address.to_c(),
                                                scan_params.to_c(),
                                                conn_params.to_c())


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_disconnect(self, conn_handle, hci_status_code = BLEHci.remote_user_terminated_connection):
        assert isinstance(hci_status_code, BLEHci), 'Invalid argument type'
        return driver.sd_ble_gap_disconnect(self.rpc_adapter, 
                                                   conn_handle,
                                                   hci_status_code.value)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gap_adv_data_set(self, adv_data = BLEAdvData(), scan_data = BLEAdvData()):
        assert isinstance(adv_data, BLEAdvData),    'Invalid argument type'
        assert isinstance(scan_data, BLEAdvData),   'Invalid argument type'
        (adv_data_len,  p_adv_data)     = adv_data.to_c()
        (scan_data_len, p_scan_data)    = scan_data.to_c()

        return driver.sd_ble_gap_adv_data_set(self.rpc_adapter,
                                              p_adv_data,
                                              adv_data_len,
                                              p_scan_data,
                                              scan_data_len)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_vs_uuid_add(self, uuid):
        assert isinstance(uuid, BLEUUID), 'Invalid argument type'
        uuid_type = driver.new_uint8()

        err_code = driver.sd_ble_uuid_vs_add(self.rpc_adapter,
                                             uuid.uuid128_to_c(),
                                             uuid_type)
        if err_code == driver.NRF_SUCCESS:
            uuid.type = driver.uint8_value(uuid_type)
        return err_code


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gattc_write(self, conn_handle, write_params):
        assert isinstance(write_params, BLEGattcWriteParams), 'Invalid argument type'
        return driver.sd_ble_gattc_write(self.rpc_adapter,
                                         conn_handle,
                                         write_params.to_c())


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gattc_prim_srvc_disc(self, conn_handle, srvc_uuid, start_handle):
        assert isinstance(srvc_uuid, (BLEUUID, NoneType)), 'Invalid argument type'
        return driver.sd_ble_gattc_primary_services_discover(self.rpc_adapter,
                                                             conn_handle,
                                                             start_handle,
                                                             srvc_uuid.uuid_to_c() if srvc_uuid else None)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gattc_char_disc(self, conn_handle, start_handle, end_handle):
        handle_range                = driver.ble_gattc_handle_range_t()
        handle_range.start_handle   = start_handle
        handle_range.end_handle     = end_handle
        return driver.sd_ble_gattc_characteristics_discover(self.rpc_adapter,
                                                            conn_handle,
                                                            handle_range)


    @NordicSemiErrorCheck
    @synchronized(api_lock)
    def ble_gattc_desc_disc(self, conn_handle, start_handle, end_handle):
        handle_range                = driver.ble_gattc_handle_range_t()
        handle_range.start_handle   = start_handle
        handle_range.end_handle     = end_handle
        return driver.sd_ble_gattc_descriptors_discover(self.rpc_adapter,
                                                        conn_handle,
                                                        handle_range)


    def status_handler(self, adapter, status_code, status_message):
        pass


    def log_message_handler(self, adapter, severity, log_message):
        pass


    @synchronized(observer_lock)
    def ble_evt_handler(self, adapter, ble_event):
        evt_id = None
        try:
            evt_id = BLEEvtID(ble_event.header.evt_id)
        except:
            logger.error('Invalid received BLE event id: 0x{:02X}'.format(ble_event.header.evt_id))
            return
        try:
            if evt_id == BLEEvtID.gap_evt_connected:
                connected_evt = ble_event.evt.gap_evt.params.connected

                for obs in self.observers:
                    obs.on_gap_evt_connected(ble_driver     = self,
                                             conn_handle    = ble_event.evt.gap_evt.conn_handle,
                                             peer_addr      = BLEGapAddr.from_c(connected_evt.peer_addr),
                                             own_addr       = BLEGapAddr.from_c(connected_evt.own_addr),
                                             role           = BLEGapRoles(connected_evt.role),
                                             conn_params    = BLEGapConnParams.from_c(connected_evt.conn_params))

            elif evt_id == BLEEvtID.gap_evt_disconnected:
                disconnected_evt = ble_event.evt.gap_evt.params.disconnected

                for obs in self.observers:
                    obs.on_gap_evt_disconnected(ble_driver  = self,
                                                conn_handle = ble_event.evt.gap_evt.conn_handle,
                                                reason      = BLEHci(disconnected_evt.reason))

            elif evt_id == BLEEvtID.gap_evt_timeout:
                timeout_evt = ble_event.evt.gap_evt.params.timeout

                for obs in self.observers:
                    obs.on_gap_evt_timeout(ble_driver   = self,
                                           conn_handle  = ble_event.evt.gap_evt.conn_handle,
                                           src          = BLEGapTimeoutSrc(timeout_evt.src))

            elif evt_id == BLEEvtID.gap_evt_adv_report:
                adv_report_evt  = ble_event.evt.gap_evt.params.adv_report
                adv_type        = None
                if not adv_report_evt.scan_rsp:
                    adv_type = BLEGapAdvType(adv_report_evt.type)

                for obs in self.observers:
                    obs.on_gap_evt_adv_report(ble_driver    = self,
                                              conn_handle   = ble_event.evt.gap_evt.conn_handle,
                                              peer_addr     = BLEGapAddr.from_c(adv_report_evt.peer_addr),
                                              rssi          = adv_report_evt.rssi,
                                              adv_type      = adv_type,
                                              adv_data      = BLEAdvData.from_c(adv_report_evt))

            elif evt_id == BLEEvtID.evt_tx_complete:
                tx_complete_evt = ble_event.evt.common_evt.params.tx_complete

                for obs in self.observers:
                    obs.on_evt_tx_complete(ble_driver   = self,
                                           conn_handle  = ble_event.evt.common_evt.conn_handle,
                                           count        = tx_complete_evt.count)

            elif evt_id == BLEEvtID.gattc_evt_write_rsp:
                write_rsp_evt   = ble_event.evt.gattc_evt.params.write_rsp

                for obs in self.observers:
                    obs.on_gattc_evt_write_rsp(ble_driver   = self,
                                               conn_handle  = ble_event.evt.gattc_evt.conn_handle,
                                               status       = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                                               error_handle = ble_event.evt.gattc_evt.error_handle,
                                               attr_handle  = write_rsp_evt.handle,
                                               write_op     = BLEGattWriteOperation(write_rsp_evt.write_op),
                                               offset       = write_rsp_evt.offset,
                                               data         = util.uint8_array_to_list(write_rsp_evt.data,
                                                                                       write_rsp_evt.len))

            elif evt_id == BLEEvtID.gattc_evt_hvx:
                hvx_evt = ble_event.evt.gattc_evt.params.hvx

                for obs in self.observers:
                    obs.on_gattc_evt_hvx(ble_driver     = self,
                                         conn_handle    = ble_event.evt.gattc_evt.conn_handle,
                                         status         = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                                         error_handle   = ble_event.evt.gattc_evt.error_handle,
                                         attr_handle    = hvx_evt.handle,
                                         hvx_type       = BLEGattHVXType(hvx_evt.type),
                                         data           = util.uint8_array_to_list(hvx_evt.data, hvx_evt.len))

            elif evt_id == BLEEvtID.gattc_evt_prim_srvc_disc_rsp:
                prim_srvc_disc_rsp_evt = ble_event.evt.gattc_evt.params.prim_srvc_disc_rsp

                services = list()
                for s in util.service_array_to_list(prim_srvc_disc_rsp_evt.services, prim_srvc_disc_rsp_evt.count):
                    services.append(BLEService.from_c(s))

                for obs in self.observers:
                    obs.on_gattc_evt_prim_srvc_disc_rsp(ble_driver  = self,
                                                        conn_handle = ble_event.evt.gattc_evt.conn_handle,
                                                        status      = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                                                        services    = services)

            elif evt_id == BLEEvtID.gattc_evt_char_disc_rsp:
                char_disc_rsp_evt = ble_event.evt.gattc_evt.params.char_disc_rsp

                characteristics = list()
                for ch in util.ble_gattc_char_array_to_list(char_disc_rsp_evt.chars, char_disc_rsp_evt.count):
                    characteristics.append(BLECharacteristic.from_c(ch))

                for obs in self.observers:
                    obs.on_gattc_evt_char_disc_rsp(ble_driver       = self,
                                                   conn_handle      = ble_event.evt.gattc_evt.conn_handle,
                                                   status           = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                                                   characteristics  = characteristics)

            elif evt_id == BLEEvtID.gattc_evt_desc_disc_rsp:
                desc_disc_rsp_evt = ble_event.evt.gattc_evt.params.desc_disc_rsp

                descriptions = list()
                for d in util.desc_array_to_list(desc_disc_rsp_evt.descs, desc_disc_rsp_evt.count):
                    descriptions.append(BLEDescriptor.from_c(d))

                for obs in self.observers:
                    obs.on_gattc_evt_desc_disc_rsp(ble_driver   = self,
                                                   conn_handle  = ble_event.evt.gattc_evt.conn_handle,
                                                   status       = BLEGattStatusCode(ble_event.evt.gattc_evt.gatt_status),
                                                   descriptions = descriptions)

        except Exception as e:
            logger.error("Exception: {}".format(str(e)))
            for line in traceback.extract_tb(sys.exc_info()[2]):
                logger.error(line) 
            logger.error("") 
