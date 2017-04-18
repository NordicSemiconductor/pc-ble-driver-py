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


class GattClientObserver(object):
    def on_gattc_event(self, gatt_client, event):
        pass

    # gattc

    def on_primary_service_discovery_response(self, gatt_client, event):
        pass

    def on_characteristic_discovery_response(self, gatt_client, event):
        pass

    def on_descriptor_discovery_response(self, gatt_client, event):
        pass

    def on_notification(self, gatt_client, event):
        pass

    def on_indication(self, gatt_client, event):
        pass

    # gap

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


class NrfDriverObserver(object):
    def on_driver_event(self, nrf_driver, event):
        pass

class NrfAdapterObserver(object):
    def on_gap_evt_adv_report(self, adapter, event):
        pass

    def on_gap_evt_timeout(self, adapter, event):
        pass

