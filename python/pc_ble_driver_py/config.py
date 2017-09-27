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

def sd_api_ver_get():
    if __conn_ic_id__ is None:
        raise RuntimeError('Connectivity IC identifier __conn_ic_id__ is not set')

    if __conn_ic_id__.upper() == "NRF51":
        _sd_api_v = 2
    elif __conn_ic_id__.upper() == "NRF52":
        _sd_api_v = 3
    else:
        raise RuntimeError('Invalid connectivity IC identifier: {}.'.format(__conn_ic_id__))
    return _sd_api_v


def conn_ic_hex_get():
    import os
    if __conn_ic_id__ is None:
        raise RuntimeError('Connectivity IC identifier __conn_ic_id__ is not set')

    if __conn_ic_id__.upper() == "NRF51":
        return os.path.join(os.path.dirname(__file__),
                        'hex', 'sd_api_v2',
                        'connectivity_1.2.0_115k2_with_s130_2.0.1.hex')
    elif __conn_ic_id__.upper() == "NRF52":
        return os.path.join(os.path.dirname(__file__),
                        'hex', 'sd_api_v3',
                        'connectivity_1.2.0_115k2_with_s132_3.0.hex')
    else:
        raise RuntimeError('Invalid connectivity IC identifier: {}.'.format(__conn_ic_id__))
