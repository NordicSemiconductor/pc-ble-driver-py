import logging
import sys
import ctypes
import os
import platform
import importlib

logger  = logging.getLogger(__name__)

driver = None

# TODO: Make sure we only run this code once.
from pc_ble_driver_py import config
nrf_sd_ble_api_ver = config.sd_api_ver_get()
# Load pc_ble_driver
SWIG_MODULE_NAME = "pc_ble_driver_sd_api_v{}".format(nrf_sd_ble_api_ver)
SHLIB_NAME = "pc_ble_driver_shared_sd_api_v{}".format(nrf_sd_ble_api_ver)

if getattr(sys, 'frozen', False):
    # we are running in a bundle
    this_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    #this_dir, this_file = os.path.split(__file__)
    import pc_ble_driver_py
    this_dir = os.path.dirname(pc_ble_driver_py.__file__)

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
    shlib_plat = 'macos_osx'
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

logger.info('Shared library: {}'.format(shlib_path))
logger.info('Swig module name: {}'.format(SWIG_MODULE_NAME))

sys.path.append(shlib_dir)
driver = importlib.import_module(SWIG_MODULE_NAME)

import pc_ble_driver_py.ble_driver_types as util
