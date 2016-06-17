from setuptools import setup, find_packages
import sys

import pc_ble_driver_py

py2 = sys.version_info[0] == 2
py3 = sys.version_info[0] == 3

if py2:
    requirements = ['enum34', 'future']
elif py3:
    requirements = ['future']


setup(
    
    name ='pc_ble_driver_py',
        
    version = pc_ble_driver_py.__version__,
    
    description = 'Python bindings for the Nordic pc-ble-driver SoftDevice serialization library',
    long_description = 'A Python interface and library for pc-ble-driver. Since the shared libraries are 32-bit applications, this package can only be used with 32-bit Python 2.7.x',
    
    url = 'https://github.com/NordicSemiconductor/pc-ble-driver-py',
        
    author = 'Nordic Semiconductor ASA',
    
    license = 'Modified BSD License',
    
    classifiers = [

        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        
        'Operating System :: MacOS :: MacOSX',
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
    }
    
    )
