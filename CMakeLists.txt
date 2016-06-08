cmake_minimum_required(VERSION 2.8.12)

# Name of the project
project (pc-ble-driver-py)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# All projects depending on pc-ble-driver need to include this first
include(pc-ble-driver/cmake/pc-ble-driver.cmake)
add_subdirectory(pc-ble-driver)

# Include folders
include_directories(${PC_BLE_DRIVER_INCLUDE_DIR})

# SWIG
find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

find_package(PythonLibs 2.7 REQUIRED)

set(PYTHON_MODULE ${PC_BLE_DRIVER_PROJECT_NAME})

include_directories(${PYTHON_INCLUDE_PATH})

#set(CMAKE_SWIG_FLAGS -threads -DPC_BLE_DRIVER_STATIC)

set(SWIG_SRC_FILE src/swig/ble_driver_py.i)

#find_library(_SHARED_LIB NAMES ${PC_BLE_DRIVER_SHARED_LIB} PATHS ${CMAKE_BINARY_DIR})

# Create a directory to put the generated output from SWIG
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/swig")

set_property(SOURCE  ${SWIG_SRC_FILE} APPEND PROPERTY SWIG_FLAGS "-threads")
set_property(SOURCE  ${SWIG_SRC_FILE} APPEND PROPERTY SWIG_FLAGS "-DPC_BLE_DRIVER_STATIC")
set_property(SOURCE  ${SWIG_SRC_FILE} APPEND PROPERTY SWIG_FLAGS "-Wall")

# Use release lib of Python even when building with DEBUG
add_definitions(
    -DSWIG_PYTHON_INTERPRETER_NO_DEBUG
)

set_property(SOURCE ${SWIG_SRC_FILE} PROPERTY CPLUSPLUS ON)
swig_add_module(${PYTHON_MODULE} python ${SWIG_SRC_FILE})

swig_link_libraries(${PYTHON_MODULE} ${PYTHON_LIBRARIES} ${PC_BLE_DRIVER_SHARED_LIB})
