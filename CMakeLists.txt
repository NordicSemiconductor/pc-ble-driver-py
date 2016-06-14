cmake_minimum_required(VERSION 3.0)

# Name of the project
project (pc-ble-driver-py)

set(PC_BLE_DRIVER_PY_OUTDIR ${CMAKE_BINARY_DIR}/outdir)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
set(CMAKE_SWIG_OUTDIR ${PC_BLE_DRIVER_PY_OUTDIR})
foreach( OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES} )
    string( TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG )
    set( CMAKE_RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR} )
    set( CMAKE_LIBRARY_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR} )
    set( CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR} )
endforeach( OUTPUTCONFIG CMAKE_CONFIGURATION_TYPES )

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

set(SWIG_I_FILE ${CMAKE_CURRENT_LIST_DIR}/swig/pc_ble_driver.i)

#find_library(_SHARED_LIB NAMES ${PC_BLE_DRIVER_SHARED_LIB} PATHS ${CMAKE_BINARY_DIR})

# Create a directory to put the generated output from SWIG
#file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/swig")

set_property(SOURCE  ${SWIG_I_FILE} APPEND PROPERTY SWIG_FLAGS "-threads")
set_property(SOURCE  ${SWIG_I_FILE} APPEND PROPERTY SWIG_FLAGS "-DPC_BLE_DRIVER_STATIC")

# Use release lib of Python even when building with DEBUG
add_definitions( -DSWIG_PYTHON_INTERPRETER_NO_DEBUG -DHAVE_ROUND=1)

# Avoid warning on Windows
if(WIN32)
    add_definitions( -DHAVE_ROUND )
endif()

set_property(SOURCE ${SWIG_I_FILE} PROPERTY CPLUSPLUS OFF)

set(SWIG_C_SRC_FILES ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE}PYTHON_wrap.c)
set_source_files_properties(SWIG_C_SRC_FILES PROPERTIES LANGUAGE CXX)

swig_add_module(${PYTHON_MODULE} python ${SWIG_I_FILE})

# These are the files required for the pc_ble_driver Python module:

# Windows
# pc_ble_driver.py
# _pc_ble_driver.pyd
# pc_ble_driver_shared.dll

# Linux
# pc_ble_driver.py
# _pc_ble_driver.so
# libpc_ble_driver_shared.so

# OS X
# pc_ble_driver.py
# _pc_ble_driver.so
# libpc_ble_driver_shared.dylib

swig_link_libraries(${PYTHON_MODULE} ${PYTHON_LIBRARIES} ${PC_BLE_DRIVER_SHARED_LIB})

set(PY_PACKAGE_DIR ${CMAKE_CURRENT_LIST_DIR}/python)
set(PY_MODULE_DIR ${PY_PACKAGE_DIR}/pc_ble_driver_py)

set(PC_BLE_DRIVER_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${CMAKE_SHARED_LIBRARY_PREFIX}${PC_BLE_DRIVER_SHARED_LIB}${CMAKE_SHARED_LIBRARY_SUFFIX})

if(WIN32)
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/win/x86_${ARCH_BITS})
    set(SWIG_WRAPPER_SHARED_LIB_EXT pyd)
elseif(APPLE)
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/osx)
    set(SWIG_WRAPPER_SHARED_LIB_EXT so)
else()
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/linux/x86_${ARCH_BITS})
    set(SWIG_WRAPPER_SHARED_LIB_EXT so)
endif()

set(SWIG_WRAPPER_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/_${PYTHON_MODULE}.${SWIG_WRAPPER_SHARED_LIB_EXT})

# Copy SWIG-generated wrapper
add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE}_REAL_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE}.py ${PY_MODULE_SHARED_LIB_DIR}
)

# Copy SWIG wrapper lib
add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE}_REAL_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy ${PC_BLE_DRIVER_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
)

# Copy DLL
add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE}_REAL_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy ${SWIG_WRAPPER_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
)

