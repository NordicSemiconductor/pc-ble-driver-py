#
# Copyright (c) 2019 Nordic Semiconductor ASA
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


from pc_ble_driver_py.ble_driver import (
    BLEDriver,
    BLEEnableParams,
    BLEConfig,
    BLEConfigConnGatt,
    BLEConfigConnGap,
)
from pc_ble_driver_py.ble_adapter import BLEAdapter
from driver_setup import Settings


def setup_adapter(
    port,
    auto_flash,
    baud_rate,
    retransmission_interval,
    response_timeout,
    driver_log_level,
):
    settings = Settings.current()

    driver = BLEDriver(
        serial_port=port,
        auto_flash=auto_flash,
        baud_rate=baud_rate,
        retransmission_interval=retransmission_interval,
        response_timeout=response_timeout,
        log_severity_level=driver_log_level,
    )

    adapter = BLEAdapter(driver)
    adapter.default_mtu = settings.mtu
    adapter.open()
    if settings.nrf_family == "NRF51":
        adapter.driver.ble_enable(
            BLEEnableParams(
                vs_uuid_count=1,
                service_changed=0,
                periph_conn_count=1,
                central_conn_count=1,
                central_sec_count=1,
            )
        )
    elif settings.nrf_family == "NRF52":
        gatt_cfg = BLEConfigConnGatt()
        gatt_cfg.att_mtu = adapter.default_mtu
        gatt_cfg.tag = Settings.CFG_TAG
        adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)

        if hasattr(settings, "event_length"):
            gap_cfg = BLEConfigConnGap()
            gap_cfg.event_length = settings.event_length
            adapter.driver.ble_cfg_set(BLEConfig.conn_gap, gap_cfg)

        adapter.driver.ble_enable()

    return adapter
