# Python bindings for the nRF5 Bluetooth Low Energy GAP/GATT driver

[![Latest version](https://img.shields.io/pypi/v/pc-ble-driver-py.svg)](https://pypi.python.org/pypi/pc-ble-driver-py)
[![License](https://img.shields.io/pypi/l/pc-ble-driver-py.svg)](https://pypi.python.org/pypi/pc-ble-driver-py)

## Introduction
pc-ble-driver-py is a serialization library over serial port that provides Python bindings
for the [nrf-ble-driver library](https://github.com/NordicSemiconductor/pc-ble-driver).

pc-ble-driver-py depends on nrf-ble-driver that is provided with the Python binding.

To run the Python bindings you will need to set up your boards to be able to communicate with your computer.
You can find additional information here:

[Hardware setup](https://github.com/NordicSemiconductor/pc-ble-driver/tree/master#hardware-setup)

## License

See the [license file](LICENSE) for details.

## Installing from PyPI

To install the latest published version from the Python Package Index simply type:

    pip install pc-ble-driver-py

**Note**: On Windows, the runtime libraries targeted when building the library must be present when running code using the library. If you get one of the following errors:

* Missing `MSVC*120.DLL` or `MSVC*140.DLL`
* `RuntimeError: Could not load shared library <path>/pc_ble_driver_shared.dll : '[Error 193] %1 is
not a valid Win32 application'`. 

please install the redistributable installer for [Visual Studio 2013](https://www.microsoft.com/en-us/download/details.aspx?id=40784) or [Visual Studio 2015](https://www.microsoft.com/en-us/download/details.aspx?id=48145) respectively. Make sure to install the one corresponding to the architecture of your **Python** installation (x86 or x64).

## Compiling from source

Before building pc-ble-driver-py you will need make nrf-ble-driver available as a CMake module. The easiest way to do this is to install it with [vcpkg](https://github.com/NordicPlayground/vcpkg).

    vcpkg install nrf-ble-driver:<[triplet](https://github.com/Microsoft/vcpkg/blob/master/docs/users/triplets.md)> --head

*TODO: remove --head argument when port PR of nrf-ble-driver is merged with MSFT master*
triplet must match the version of python you are building the binding for. To see the triplets supported, type:

    vcpkg help triplet

Running vcpkg install starts compilation and installation of nrf-ble-driver.

Before compiling the binding do the following:

* make sure the VCPKG_ROOT environment variable is set to the location of the vcpkg directory
* install the python install requirements:

    pip install -r requirements-dev.txt

Compilation of the binding can be initiated with [tox](https://tox.readthedocs.io/en/latest/).
tox is a generic virtualenv management and test command line tool.

The config tox.ini contains the Python interpreter versions currently supported. Python wheels will be created for every supported version it finds on the system.


### Dependencies

To build this project you will need the following tools:

* [SWIG](http://www.swig.org/) (>= 3.10)
* [Python](https://www.python.org/) (>= 2.7 && <= 3.0)
* [vcpkg](https://github.com/NordicPlayground/vcpkg) (TODO: update repo URL when port PR of nrf-ble-driver is merged with MSFT master)
* A C/C++ toolchain (should already have been installed to build nrf-ble-driver)


See the following sections for platform-specific instructions on the installation of the dependencies.

*TODO: rewrite below instructions to reflect that nrf-ble-driver is available as a cmake module and that boost is no longer used*

#### Windows 

* Install the latest CMake stable release by downloading the Windows Installer from:

[CMake Downloads](https://cmake.org/download/)

* Install the latest SWIG stable release by downloading the `swigwin-x.y.z` package from:

[SWIG Downloads](http://www.swig.org/download.html)

Then extract it into a folder of your choice. Append the SWIG folder to your PATH, for example if you have installed
SWIG in `c:\swig\swigwin-x.y.z`:

    PATH=%PATH%;c:\swig\swigwin-x.y.z;

* Install the latest Python 2 Release by downloading the installer from:

[Python Windows Downloads](https://www.python.org/downloads/windows/)

**Note**: Select the Python architecture (32 or 64-bit) that you plan to build for.

Install Microsoft Visual Studio. The following versions are supported:

* Visual Studio 2015 (MSVC 14.0)

Open a Microsoft Visual Studio Command Prompt and issue the following from the root folder of the repository:

    > cd build
    > cmake -G "Visual Studio XX <Win64>" <-DBOOST_LIBRARYDIR="<Boost libs path>>" ..
    > msbuild ALL_BUILD.vcxproj </p:Configuration=<CFG>>

**Note**: Select Visual Sutio 14 with the `-G "Visual Studio XX"` option.

**Note**: Add `Win64` to the `-G` option to build a 64-bit version of the driver.

**Note**: Optionally select the location of the Boost libraries with the `-DBOOST_LIBRARYDIR` option.

**Note**: Optionally select the build configuration with the `/p:Configuration=` option. Typically `Debug`, `Release`, `MinSizeRel` and `RelWithDebInfo` are available.

The results of the build will be placed in `build\outdir` and the distributable files will be copied to `python\pc_ble_driver_py\lib\win\x86_<arch>` and `python\pc_ble_driver_py\hex`.

##### Examples

Building for 32-bit Python with 64-bit Visual Studio 15:

    > cmake -G "Visual Studio 14" ..

Building for 64-bit Python with 64-bit Visual Studio 15 pointing to a 64-bit Boost build:

    > cmake -G "Visual Studio 14 Win64" -DBOOST_LIBRARYDIR="c:\boost\boost_1_61_0\stage\x64" ..

#### Ubuntu Linux

Install the required packages to build the bindings:

    $ sudo apt-get install cmake swig libudev-dev python python-dev

Then change to the root folder of the repository and issue the following commands:

    $ cd build
    > cmake -G "Unix Makefiles" <-DCMAKE_BUILD_TYPE=<build_type>> <-DARCH=<x86_32,x86_64>> <-DBOOST_LIBRARYDIR="<Boost libs path>>" ..
    $ make

**Note**: Optionally Select the build configuration with the `-DCMAKE_BUILD_TYPE` option. Typically `Debug`, `Release`, `MinSizeRel` and `RelWithDebInfo` are available.

**Note**: Optionally select the target architecture (32 or 64-bit) using the `-DARCH` option.

**Note**: Optionally select the location of the Boost libraries with the `-DBOOST_LIBRARYDIR` option.

The results of the build will be placed in `build/outdir` and the distributable files will be copied to `python/pc_ble_driver_py/lib/linux\x86_<arch>` and `python\pc_ble_driver_py\hex`.

#### macOS (OS X) 10.11 and later

Install cmake and swig with Homebrew with the `brew` command on a terminal:

    $ brew install cmake
    $ brew install swig

Then change to the root folder of the repository and issue the following commands:

    $ cd build
    $ cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE= <build_type> ..
    $ make

**Note**: Optionally Select the build configuration with the `-DCMAKE_BUILD_TYPE` option. Typically `Debug`, `Release`, `MinSizeRel` and `RelWithDebInfo` are available.

The results of the build will be placed in `build/outdir` and the distributable files will be copied to `python/pc_ble_driver_py/lib/macos_osx` and `python\pc_ble_driver_py\hex`.
