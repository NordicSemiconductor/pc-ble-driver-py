cmake_minimum_required(VERSION 2.8.12)

# Name of the project
project (pc-ble-driver-py)

# All projects depending on pc-ble-driver need to include this first
include(pc-ble-driver/cmake/pc-ble-driver.cmake)
add_subdirectory(pc-ble-driver)

# Include folders
include_directories(${PC_BLE_DRIVER_INCLUDE_DIR})

# SWIG
find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

find_package(PythonLibs REQUIRED)

set(PYTHON_MODULE ${PC_BLE_DRIVER_PROJECT_NAME})

include_directories(${PYTHON_INCLUDE_PATH})

set(CMAKE_SWIG_FLAGS "-threads")

# Add definitions used by compiler when compiling source files
add_definitions(
    -DSD_RPC_EXPORTS
)

set(SWIG_SRC_FILE src/swig/ble_driver_py.i)

#find_library(_SHARED_LIB NAMES ${PC_BLE_DRIVER_SHARED_LIB} PATHS ${CMAKE_BINARY_DIR})

# Create a directory to put the generated output from SWIG
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/swig")

set_property(SOURCE  ${SWIG_SRC_FILE} PROPERTY SWIG_FLAGS "-Wall")

swig_add_module(${PYTHON_MODULE} python ${SWIG_SRC_FILE})

set_source_files_properties(${SWIG_SRC_FILE} PROPERTIES CPLUSCPLUS ON)

swig_link_libraries(${PYTHON_MODULE} ${PYTHON_LIBRARIES} ${PC_BLE_DRIVER_SHARED_LIB})
