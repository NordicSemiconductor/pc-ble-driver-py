# Python bindings for the nRF5 Bluetooth Low Energy GAP/GATT driver

[![Latest version](https://img.shields.io/pypi/v/pc-ble-driver-py.svg)](https://pypi.python.org/pypi/pc-ble-driver-py)
[![License](https://img.shields.io/pypi/l/pc-ble-driver-py.svg)](https://pypi.python.org/pypi/pc-ble-driver-py)

## Introduction
pc-ble-driver-py is a serialization library over serial port that provides Python bindings
for the [nrf-ble-driver library](https://github.com/NordicSemiconductor/pc-ble-driver).

The Python bindings require that the development kit you use is programmed with the correct connectivity firmware. [Hardware setup](https://github.com/NordicSemiconductor/pc-ble-driver/tree/master#hardware-setup)

## License

See the [license file](LICENSE) for details.

## Disclaimer
pc-ble-driver-py does not implement or enable all of the features of the underlying pc-ble-driver (C/C++) library. Features have mostly been added on a need basis. Functions or features that have been added may also be lacking sub-features. However, as the underlying language bindings have been auto-generated, it is often the case that features can be made available by adding to the conversion-layer found in ´ble_driver.py´.
If you find features missing that you would like to have in, you are welcome to propose an implementation through a pull request.

## Installing from PyPI

To install the latest published version from the Python Package Index simply type:

    pip install pc-ble-driver-py

**Note**: On Windows, the runtime libraries targeted when building the library must be present when running code using the library. If you get one of the following errors:

* Missing `MSVC*120.DLL` or `MSVC*140.DLL`
* `RuntimeError: Could not load shared library <path>/pc_ble_driver_shared.dll : '[Error 193] %1 is
not a valid Win32 application'`. 

please install the redistributable installer for [Visual Studio 2013](https://www.microsoft.com/en-us/download/details.aspx?id=40784) or [Visual Studio 2015](https://www.microsoft.com/en-us/download/details.aspx?id=48145) respectively. Make sure to install the one corresponding to the architecture of your **Python** installation (x86 or x64).

### macOS limitations
The binary distribution of pc-ble-driver-py will only work with the official Python versions, not the one provided with macOS or a brew install.

## Building from source

Before building pc-ble-driver-py you will need to install nrf-ble-driver as a CMake module. The easiest way to do this is to install it with [vcpkg](https://github.com/NordicPlayground/vcpkg).

    vcpkg install nrf-ble-driver

To use a different triplet than [the default one](https://github.com/microsoft/vcpkg/blob/master/docs/users/triplets.md#additional-remarks), see documentation in vcpkg:

    vcpkg help triplet
    vcpkg help install

Triplet must match the version of python you are building the binding for.

Running vcpkg install starts compilation and installation of nrf-ble-driver.

Before compiling the binding do the following:

* Make sure that the VCPKG_ROOT environment variable is set to the location of the vcpkg directory
* install the python install requirements:


        pip install -r requirements-dev.txt



Building a release of the binding and automatically running tests afterwards can be initiated with [tox](https://tox.readthedocs.io/en/latest/). tox is a generic virtualenv management and test command line tool.

Two development kits must be attached to the computer and the UART ports for them must be specified through envionment variables (PORT_A, PORT_B).

    > export PORT_A=/dev/ttyACM0
    > export PORT_B=/dev/ttyACM1
    > tox

The config tox.ini contains the Python interpreter versions currently supported. Python wheels will be created for every supported version it finds on the system. To run tox, type:

    tox -e <python environment> # For example py37, if you have that installed

See [tox.ini](tox.ini) for more configuration of the build and running of tests.


To build a release build of the binding run the following command:

    > python setup.py bdist_wheel --build-type Release

To build a debug build of the binding:

    > python setup.py bdist_wheel --build-type Debug


The wheel packages are found in the `dist` directory




### Dependencies

To build this project you will need the following tools:

* [SWIG](http://www.swig.org/) (>= 4.0)
* [Python](https://www.python.org/) (>=3.6)
* [vcpkg](https://github.com/NordicPlayground/vcpkg)
* A C/C++ toolchain (should already have been installed to build nrf-ble-driver)


See the following sections for platform-specific instructions on the installation of the dependencies.


#### Windows

* Install the latest CMake stable release by downloading the Windows Installer from [CMake site](https://cmake.org/download/)

* Install the latest SWIG stable release by downloading the `swigwin-x.y.z` package from [SWIG site](http://www.swig.org/download.html)

Then extract it into a folder of your choice. Append the SWIG folder to your PATH, for example if you have installed
SWIG in `c:\swig\swigwin-x.y.z`:

    PATH=%PATH%;c:\swig\swigwin-x.y.z;

* Install Python 3.6 or newer by downloading the installer from [Python Windows Downloads](https://www.python.org/downloads/windows/)

**Note**: Select the Python architecture (32 or 64-bit) that you plan to build for.

Install Microsoft Visual Studio matching the Python version. For an overview of recommended versions of Visual Studio to use, see [this table](https://github.com/scikit-build/scikit-build/blob/0.9.0/docs/generators.rst#visual-studio-ide).

The distributable files will be placed in `dist`.


#### Ubuntu Linux

Install the required packages to build the bindings:

    $ sudo apt-get install cmake swig libudev-dev python python-dev


#### macOS (OS X) 10.11 and later

Install cmake and swig with [Homebrew](https://brew.sh/) with the `brew` command on a terminal:

    $ brew install cmake
    $ brew install swig

