# Python bindings for the nRF5 Bluetooth Low Energy GAP/GATT driver

## Introduction
pc-ble-driver-py is a serialization library over serial port that provides Python bindings
for the [pc-ble-driver  library](https://github.com/NordicSemiconductor/pc-ble-driver) library.

pc-ble-driver-py depends on the pc-ble-driver repository referrenced as a submodule.

These bindings include two different components:

* A shared library written in C that encapsulates the SoftDevice API and serializes it over UART.
* A set of Python files generated with SWIG that present the shared library API to Python applications.

# Installation procedure

Before building pc-ble-driver-py you will need to have Boost installed and some of its libraries statically compiled.
To install and compile Boost, please follow the instructions here:

[Installing and building Boost](https://github.com/NordicSemiconductor/pc-ble-driver/tree/self_contained_driver#installing-and-building-boost)

Assuming that you have built the Boost libraries and installed the tools required to do so, you can now build and install the Python bindings and the accompanying shared library.

## Dependencies

To build this project you will need the following tools:

* [CMake](https://cmake.org/) (>=2.8.12)
* [SWIG](http://www.swig.org/)
* [Python](https://www.python.org/) (>= 2.7 && <= 3.0)
* A C/C++ toolchain (should already have been installed to build Boost)

See the following sections for platform-specific instructions on the installation of the dependencies.

### Windows 

* Install the latest CMake stable release by downloading the Windows Installer from:

[CMake Downloads](https://cmake.org/download/)

* Install the latest SWIG stable release by downloading the `swigwin-x.y.z` package from:

[SWIG Downloads](http://www.swig.org/download.html)

Then extract it into a folder of your choice. Append the SWIG folder to your PATH, for example if you have installed
SWIG in `c:\swig\swigwin-x.y.z`:

    PATH=%PATH%;c:\swig\swigwin-x.y.z;

* Install the latest Python 2 Release by downloading the installer from:

[Python Windows Downloads](https://www.python.org/downloads/windows/)

Install Microsoft Visual Studio. The following versions supported are:

* Visual Studio 2013 (MSVC 12.0)
* Visual Studio 2015 (MSVC 14.0)

Open a Microsoft Visual Studio Command Prompt and issue the following from the root folder of the repository:

    > cmake -G "Visual Studio XX"
    > msbuild ALL_BUILD.vcxproj

**Note**: Select Visual Sutio 12 or 14 `-G "Visual Studio XX"` option.

**Note**: Refer to the [compiler list](http://www.boost.org/build/doc/html/bbv2/reference/tools.html#bbv2.reference.tools.compilers) of the Boost documentation 
to find the version of the MSVC that you need to provide using the `toolset=` option.

### Ubuntu Linux

Install the required packages to build Boost:

    $ sudo apt-get install install cmake swig libudev-dev python python-dev

Then change to the root folder of the repository and issue the following commands:

    $ cmake -G "Unix Makefiles"
    $ make

### OS X 10.11 and later

Install cmake and swig with Homebrew with the `brew` command on a terminal:

    $ brew install boost
    $ brew install swig

Then change to the root folder of the repository and issue the following commands:

    $ cmake -G "Unix Makefiles"
    $ make

