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
from enum       import Enum
from types      import NoneType

from nrf_dll_load import driver, util

logger = logging.getLogger(__name__)


# TODO:
# * Implement _all_ structs from ble_gap.h, ble_common.h, ble_gattc.h, ...


#################### Common ################
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


class BLEUUIDBase(object):
    def __init__(self, vs_uuid_base=None, uuid_type=None):
        assert isinstance(vs_uuid_base, (list, NoneType)), 'Invalid argument type'
        assert isinstance(uuid_type, (int, long, NoneType)), 'Invalid argument type'
        if (vs_uuid_base is None) and uuid_type is None:
            self.base   = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00,
                           0x80, 0x00, 0x00, 0x80, 0x5F, 0x9B, 0x34, 0xFB]
            self.type   = driver.BLE_UUID_TYPE_BLE

        else:
            self.base   = vs_uuid_base
            self.type   = uuid_type


    @classmethod
    def from_c(cls, uuid):
        return cls(uuid_type = uuid.type)


    def to_c(self):
        lsb_list        = self.base[::-1]
        self.__array    = util.list_to_uint8_array(lsb_list)
        uuid            = driver.ble_uuid128_t()
        uuid.uuid128    = self.__array.cast()
        return uuid


class BLEUUID(object):
    class Standard(Enum):
        unknown             = 0x0000
        service_primary     = 0x2800
        service_secondary   = 0x2801
        characteristic      = 0x2803
        cccd                = 0x2902
        battery_level       = 0x2A19
        heart_rate          = 0x2A37


    def __init__(self, value, base=BLEUUIDBase()):
        assert isinstance(base, BLEUUIDBase), 'Invalid argument type'
        self.base   = base
        try:
            self.value  = value if isinstance(value, BLEUUID.Standard) else BLEUUID.Standard(value)
        except(ValueError):
            self.value  = value


    def __str__(self):
        if isinstance(self.value, BLEUUID.Standard):
            return '0x{:02X} ({})'.format(self.value.value, self.value)
        else:
            return '0x{:02X}'.format(self.value)


    @classmethod
    def from_c(cls, uuid):
        return cls(value = uuid.uuid, base = BLEUUIDBase.from_c(uuid))


    def to_c(self):
        assert self.base.type is not None, 'Vendor specific UUID not registered'
        uuid = driver.ble_uuid_t()
        if self.value is instance(BLEUUID.Standard):
            uuid.uuid = self.value.value
        else:
            uuid.uuid = self.value
        uuid.type = self.base.type
        return uuid


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

class BLEGapSecStatus(Enum):
    success                 = driver.BLE_GAP_SEC_STATUS_SUCCESS
    timeout                 = driver.BLE_GAP_SEC_STATUS_TIMEOUT
    pdu_invalid             = driver.BLE_GAP_SEC_STATUS_PDU_INVALID
    passkey_entry_failed    = driver.BLE_GAP_SEC_STATUS_PASSKEY_ENTRY_FAILED
    oob_not_available       = driver.BLE_GAP_SEC_STATUS_OOB_NOT_AVAILABLE
    auth_req                = driver.BLE_GAP_SEC_STATUS_AUTH_REQ
    confirm_value           = driver.BLE_GAP_SEC_STATUS_CONFIRM_VALUE
    pairing_not_supp        = driver.BLE_GAP_SEC_STATUS_PAIRING_NOT_SUPP
    enc_key_size            = driver.BLE_GAP_SEC_STATUS_ENC_KEY_SIZE
    smp_cmd_unsupported     = driver.BLE_GAP_SEC_STATUS_SMP_CMD_UNSUPPORTED
    unspecified             = driver.BLE_GAP_SEC_STATUS_UNSPECIFIED
    repeated_attempts       = driver.BLE_GAP_SEC_STATUS_REPEATED_ATTEMPTS
    invalid_params          = driver.BLE_GAP_SEC_STATUS_INVALID_PARAMS
    dhkey_failure           = driver.BLE_GAP_SEC_STATUS_DHKEY_FAILURE
    num_comp_failure        = driver.BLE_GAP_SEC_STATUS_NUM_COMP_FAILURE
    br_edr_in_prog          = driver.BLE_GAP_SEC_STATUS_BR_EDR_IN_PROG
    x_trans_key_disallowed  = driver.BLE_GAP_SEC_STATUS_X_TRANS_KEY_DISALLOWED

#################### Gap ##################
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
    security_req    = driver.BLE_GAP_TIMEOUT_SRC_SECURITY_REQUEST
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
        addr_list = util.uint8_array_to_list(addr.addr, driver.BLE_GAP_ADDR_LEN)
        addr_list.reverse()
        return cls(addr_type    = BLEGapAddr.Types(addr.addr_type),
                   addr         = addr_list)

    @classmethod
    def from_string(cls, addr_string):
        addr, addr_flag = addr_string.split(',')
        addr_list = [int(i, 16) for i in addr.split(':')]

        #print addr_string, addr_list[-1], addr_list[-1] & 0b11000000, 0b11000000
        #print addr_string, addr_list[-1], addr_list[-1] & 0b10000000, 0b10000000
        if addr_flag in ['p', 'public']:
            addr_type = BLEGapAddr.Types.public
        elif (addr_list[0] & 0b11000000) == 0b00000000:
            addr_type = BLEGapAddr.Types.random_private_non_resolvable
        elif (addr_list[0] & 0b11000000) == 0b01000000:
            addr_type = BLEGapAddr.Types.random_private_resolvable
        elif (addr_list[0] & 0b11000000) == 0b11000000:
            addr_type = BLEGapAddr.Types.random_static
        else:
            raise ValueError("Provided random address do not follow rules") # TODO: Improve error message

        return cls(addr_type, addr_list)


    def to_c(self):
        addr_array      = util.list_to_uint8_array(self.addr[::-1])
        addr            = driver.ble_gap_addr_t()
        addr.addr_type  = self.addr_type.value
        addr.addr       = addr_array.cast()
        return addr

    def get_addr_type_str(self):
        if   self.addr_type == BLEGapAddr.Types.public:
            return 'public'
        elif self.addr_type == BLEGapAddr.Types.random_private_non_resolvable:
            return 'nonres'
        elif self.addr_type == BLEGapAddr.Types.random_private_resolvable:
            return 'res'
        elif self.addr_type == BLEGapAddr.Types.random_static:
            return 'static'
        else:
            return 'err {0:02b}'.format((self.AddressLtlEnd[-1] >> 6) & 0b11)

    def get_addr_str(self):
        return '"%s" (% 6s)' % (self, self.get_addr_type_str())

    def __eq__(self, other):
        if not isinstance(other, BLEGapAddr):
            other = BLEGapAddr.from_string(str(other))
        return str(self) == str(other)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return str(self)

    def get_addr_flag(self):
        return 'p' if self.addr_type == BLEGapAddr.Types.public else 'r'

    def __str__(self):
        return '%s,%s' % (':'.join(['%02X' % i for i in self.addr]), self.get_addr_flag())

    def __repr__(self):
        return "%s.from_string('%s,%s')" % (self.__class__.__name__,
                ':'.join(['%02X' % i for i in self.addr]), self.get_addr_flag())



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
            try:
                ad_len  = ad_list[index]
                ad_type = ad_list[index + 1]
                offset  = index + 2
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
#################### SMP ##################

class BLEGapSecLevels(object):
    def __init__(self, lv1, lv2, lv3, lv4):
        self.lv1 = lv1
        self.lv2 = lv2
        self.lv3 = lv3
        self.lv4 = lv4

    @classmethod
    def from_c(cls, sec_level):
        return cls(lv1 = sec_level.lv1,
                   lv2 = sec_level.lv2,
                   lv3 = sec_level.lv3,
                   lv4 = sec_level.lv4)

    def to_c(self):
        sec_level     = driver.ble_gap_sec_levels_t()
        sec_level.lv1 = self.lv1
        sec_level.lv2 = self.lv2
        sec_level.lv3 = self.lv3
        sec_level.lv4 = self.lv4
        return sec_level

    def __repr__(self):
        return "%s(lv1=%r, lv2=%r, lv3=%r, lv4=%r)" % (self.__class__.__name__,
                self.lv1, self.lv2, self.lv3, self.lv4)

class BLEGapSecKeyDist(object):
    def __init__(self, enc_key=False, id_key=False, sign_key=False, link_key=False):
        self.enc_key    = enc_key
        self.id_key     = id_key
        self.sign_key   = sign_key
        self.link_key   = link_key

    @classmethod
    def from_c(cls, kdist):
        return cls(enc_key       = kdist.enc,
                   id_key        = kdist.id,
                   sign_key      = kdist.sign,
                   link_key      = kdist.link)

    def to_c(self):
        kdist       = driver.ble_gap_sec_kdist_t()
        kdist.enc   = self.enc_key
        kdist.id    = self.id_key
        kdist.sign  = self.sign_key
        kdist.link  = self.link_key
        return kdist

    def __repr__(self):
        return "%s(enc_key=%r, id_key=%r, sign_key=%r, link_key=%r)" % (self.__class__.__name__,
                self.enc_key, self.id_key, self.sign_key, self.link_key)

class BLEGapSecParams(object):
    def __init__(self, bond, mitm, le_sec_pairing, keypress_noti, io_caps, oob, min_key_size, max_key_size, kdist_own, kdist_peer):
        self.bond           = bond
        self.mitm           = mitm
        self.le_sec_pairing = le_sec_pairing
        self.keypress_noti  = keypress_noti
        self.io_caps        = io_caps
        self.oob            = oob
        self.min_key_size   = min_key_size
        self.max_key_size   = max_key_size
        self.kdist_own      = kdist_own
        self.kdist_peer     = kdist_peer

    @classmethod
    def from_c(cls, sec_params):
        return cls(bond             = sec_params.bond,
                   mitm             = sec_params.mitm,
                   le_sec_pairing   = sec_params.lesc,
                   keypress_noti    = sec_params.keypress,
                   io_caps          = sec_params.io_caps,
                   oob              = sec_params.oob,
                   min_key_size     = sec_params.min_key_size,
                   max_key_size     = sec_params.max_key_size,
                   kdist_own        = BLEGapSecKeyDist.from_c(sec_params.kdist_own),
                   kdist_peer       = BLEGapSecKeyDist.from_c(sec_params.kdist_peer))

    def to_c(self):
        sec_params              = driver.ble_gap_sec_params_t()
        sec_params.bond         = self.bond
        sec_params.mitm         = self.mitm
        sec_params.lesc         = self.le_sec_pairing
        sec_params.keypress     = self.keypress_noti
        sec_params.io_caps      = self.io_caps
        sec_params.oob          = self.oob
        sec_params.min_key_size = self.min_key_size
        sec_params.max_key_size = self.max_key_size
        sec_params.kdist_own    = self.kdist_own.to_c()
        sec_params.kdist_peer   = self.kdist_peer.to_c()
        return sec_params

    def __repr__(self):
        return "%s(bond=%r, mitm=%r, le_sec_pairing=%r, keypress_noti=%r, io_caps=%r, oob=%r, min_key_size=%r, max_key_size=%r, kdist_own=%r, kdist_peer=%r)" % (
                self.__class__.__name__, self.bond, self.mitm, self.le_sec_pairing, self.keypress_noti, self.io_caps,
                self.oob, self.min_key_size, self.max_key_size, self.kdist_own, self.kdist_peer,)

class BLEGapSecKeyset(object):
    def __init__(self):
        self.sec_keyset                 = driver.ble_gap_sec_keyset_t()
        keys_own                        = driver.ble_gap_sec_keys_t()
        self.sec_keyset.keys_own        = keys_own

        keys_peer                       = driver.ble_gap_sec_keys_t()
        keys_peer.p_enc_key             = driver.ble_gap_enc_key_t()
        keys_peer.p_enc_key.enc_info    = driver.ble_gap_enc_info_t()
        keys_peer.p_enc_key.master_id   = driver.ble_gap_master_id_t()
        keys_peer.p_id_key              = driver.ble_gap_id_key_t()
        keys_peer.p_id_key.id_info      = driver.ble_gap_irk_t()
        keys_peer.p_id_key.id_addr_info = driver.ble_gap_addr_t()
        #keys_peer.p_sign_key            = driver.ble_gap_sign_info_t()
        #keys_peer.p_pk                  = driver.ble_gap_lesc_p256_pk_t()
        self.sec_keyset.keys_peer       = keys_peer


    @classmethod
    def from_c(cls, sec_params):
        raise NotImplemented()

    def to_c(self):
        return self.sec_keyset



#################### Gatt ##################



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
    success                     = driver.BLE_GATT_STATUS_SUCCESS
    unknown                     = driver.BLE_GATT_STATUS_UNKNOWN
    invalid                     = driver.BLE_GATT_STATUS_ATTERR_INVALID
    invalid_handle              = driver.BLE_GATT_STATUS_ATTERR_INVALID_HANDLE
    read_not_permitted          = driver.BLE_GATT_STATUS_ATTERR_READ_NOT_PERMITTED
    write_not_permitted         = driver.BLE_GATT_STATUS_ATTERR_WRITE_NOT_PERMITTED
    invalid_pdu                 = driver.BLE_GATT_STATUS_ATTERR_INVALID_PDU
    insuf_authentication        = driver.BLE_GATT_STATUS_ATTERR_INSUF_AUTHENTICATION
    request_not_supported       = driver.BLE_GATT_STATUS_ATTERR_REQUEST_NOT_SUPPORTED
    invalid_offset              = driver.BLE_GATT_STATUS_ATTERR_INVALID_OFFSET
    insuf_authorization         = driver.BLE_GATT_STATUS_ATTERR_INSUF_AUTHORIZATION
    prepare_queue_full          = driver.BLE_GATT_STATUS_ATTERR_PREPARE_QUEUE_FULL
    attribute_not_found         = driver.BLE_GATT_STATUS_ATTERR_ATTRIBUTE_NOT_FOUND
    attribute_not_long          = driver.BLE_GATT_STATUS_ATTERR_ATTRIBUTE_NOT_LONG
    insuf_enc_key_size          = driver.BLE_GATT_STATUS_ATTERR_INSUF_ENC_KEY_SIZE
    invalid_att_val_length      = driver.BLE_GATT_STATUS_ATTERR_INVALID_ATT_VAL_LENGTH
    unlikely_error              = driver.BLE_GATT_STATUS_ATTERR_UNLIKELY_ERROR
    insuf_encryption            = driver.BLE_GATT_STATUS_ATTERR_INSUF_ENCRYPTION
    unsupported_group_type      = driver.BLE_GATT_STATUS_ATTERR_UNSUPPORTED_GROUP_TYPE
    insuf_resources             = driver.BLE_GATT_STATUS_ATTERR_INSUF_RESOURCES
    rfu_range1_begin            = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE1_BEGIN
    rfu_range1_end              = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE1_END
    app_begin                   = driver.BLE_GATT_STATUS_ATTERR_APP_BEGIN
    app_end                     = driver.BLE_GATT_STATUS_ATTERR_APP_END
    rfu_range2_begin            = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE2_BEGIN
    rfu_range2_end              = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE2_END
    rfu_range3_begin            = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE3_BEGIN
    rfu_range3_end              = driver.BLE_GATT_STATUS_ATTERR_RFU_RANGE3_END
    cps_cccd_config_error       = driver.BLE_GATT_STATUS_ATTERR_CPS_CCCD_CONFIG_ERROR
    cps_proc_alr_in_prog        = driver.BLE_GATT_STATUS_ATTERR_CPS_PROC_ALR_IN_PROG
    cps_out_of_range            = driver.BLE_GATT_STATUS_ATTERR_CPS_OUT_OF_RANGE



class BLEGattExecWriteFlag(Enum):
    prepared_cancel = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_CANCEL
    prepared_write  = driver.BLE_GATT_EXEC_WRITE_FLAG_PREPARED_WRITE
    unused          = 0x00



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
        self.__data_array       = util.list_to_uint8_array(self.data)
        write_params            = driver.ble_gattc_write_params_t()
        write_params.p_value    = self.__data_array.cast()
        write_params.flags      = self.flags.value
        write_params.handle     = self.handle
        write_params.offset     = self.offset
        write_params.len        = len(self.data)
        write_params.write_op   = self.write_op.value

        return write_params


class BLEDescriptor(object):
    def __init__(self, uuid, handle):
        self.handle = handle
        self.uuid   = uuid


    @classmethod
    def from_c(cls, gattc_desc):
        return cls(uuid     = BLEUUID.from_c(gattc_desc.uuid),
                   handle   = gattc_desc.handle)


class BLECharacteristic(object):
    def __init__(self, uuid, handle_decl, handle_value):
        self.uuid           = uuid
        self.handle_decl    = handle_decl
        self.handle_value   = handle_value
        self.end_handle     = None
        self.descs          = list()


    @classmethod
    def from_c(cls, gattc_char):
        return cls(uuid         = BLEUUID.from_c(gattc_char.uuid),
                   handle_decl  = gattc_char.handle_decl,
                   handle_value = gattc_char.handle_value)


class BLEService(object):
    def __init__(self, uuid, start_handle, end_handle):
        self.uuid           = uuid
        self.start_handle   = start_handle
        self.end_handle     = end_handle
        self.chars          = list()

    @classmethod
    def from_c(cls, gattc_service):
        return cls(uuid         = BLEUUID.from_c(gattc_service.uuid),
                   start_handle = gattc_service.handle_range.start_handle,
                   end_handle   = gattc_service.handle_range.end_handle)

    # TODO: What is this?
    def char_add(self, char):
        char.end_handle = self.end_handle
        self.chars.append(char)
        if len(self.chars) > 1:
            self.chars[-2].end_handle = char.handle_decl - 1
