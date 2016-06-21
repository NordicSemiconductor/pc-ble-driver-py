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
from setuptools import setup, find_packages
import sys

import pc_ble_driver_py

py2 = sys.version_info[0] == 2
py3 = sys.version_info[0] == 3

if py2:
    requirements = ['enum34', 'wrapt', 'future']
elif py3:
    requirements = ['wrapt', 'future']


setup(
    
    name ='pc_ble_driver_py',
        
    version = pc_ble_driver_py.__version__,
    
    description = 'Python bindings for the Nordic pc-ble-driver SoftDevice serialization library',
    long_description = 'A Python interface and library for pc-ble-driver. This allows Python applications to interface with a Nordic Semiconductor IC (both nRF51 and nRF52 series) over a serial port to obtain access to the full serialized SoftDevice API. This package is compatible with 2.7 Python on both 32 and 64-bit architectures on Windows, Linux and macOS (OS X).',

    url = 'https://github.com/NordicSemiconductor/pc-ble-driver-py',
        
    author = 'Nordic Semiconductor ASA',
    
    license = 'Modified BSD License',
    
    classifiers = [

        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',

        'Topic :: System :: Networking',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: Software Development :: Embedded Systems',
        
        'License :: Other/Proprietary License',

        'Programming Language :: Python :: 2.7',
    ],
    
    keywords = 'nordic nrf51 nrf52 ble bluetooth softdevice serialization bindings pc-ble-driver pc-ble-driver-py pc_ble_driver pc_ble_driver_py',
     
    install_requires = requirements,
     
    packages = find_packages(),
    package_data = { 
                'pc_ble_driver_py.lib.win.x86_32': ['*.pyd', '*.dll', '*.txt'],
                'pc_ble_driver_py.lib.win.x86_64': ['*.pyd', '*.dll', '*.txt'],
                'pc_ble_driver_py.lib.linux.x86_32': ['*.so', '*.txt'],
                'pc_ble_driver_py.lib.linux.x86_64': ['*.so', '*.txt'],
                'pc_ble_driver_py.lib.macos_osx': ['*.so', '*.dylib', '*.txt'],
                'pc_ble_driver_py.hex': ['*.hex', '*.patch']
    }
    
    )
