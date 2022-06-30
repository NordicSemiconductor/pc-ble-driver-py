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

# Connectivity IC identifier
# This variable needs to be set before importing pc_ble_driver_py from external Python code
# Currently functional variants are:
#
# * "NRF51"
# * "NRF52"
__conn_ic_id__ = None

import os


def sd_api_ver_get():
    if __conn_ic_id__ is None:
        raise RuntimeError("Connectivity IC identifier __conn_ic_id__ is not set")

    if __conn_ic_id__.upper() == "NRF51":
        _sd_api_v = 2
    elif __conn_ic_id__.upper() == "NRF52":
        _sd_api_v = 5
    else:
        raise RuntimeError(
            "Invalid connectivity IC identifier: {}.".format(__conn_ic_id__)
        )
    return _sd_api_v


def _get_hex_path(sd_api_type="s132", sd_api_version="5.1.0"):
    return os.path.join(
        os.path.dirname(__file__),
        "hex",
        "sd_api_v%s" % sd_api_version.split(".")[0],
        "connectivity_%s_1m_with_%s_%s.hex"
        % (get_connectivity_hex_version(), sd_api_type, sd_api_version),
    )


def conn_ic_hex_get():
    if __conn_ic_id__ is None:
        raise RuntimeError("Connectivity IC identifier __conn_ic_id__ is not set")

    if __conn_ic_id__.upper() == "NRF51":
        return _get_hex_path(sd_api_type="s130", sd_api_version="2.0.1")
    elif __conn_ic_id__.upper() == "NRF52":
        return _get_hex_path(sd_api_type="s132", sd_api_version="5.1.0")
    else:
        raise RuntimeError(
            "Invalid connectivity IC identifier: {}.".format(__conn_ic_id__)
        )


def get_connectivity_hex_version():
    return "4.1.4"


def get_connectivity_hex_baud_rate():
    return 1000000
