cmake_minimum_required(VERSION 3.13)

# Name of the project
project (pc-ble-driver-py)

set(PC_BLE_DRIVER_PY_OUTDIR ${CMAKE_BINARY_DIR}/outdir)

#set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
#set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
#set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
set(CMAKE_SWIG_OUTDIR ${PC_BLE_DRIVER_PY_OUTDIR})

#foreach(OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES})
#    string(TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG)
#    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR})
#    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR})
#    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PC_BLE_DRIVER_PY_OUTDIR})
#endforeach()

# All projects depending on pc-ble-driver need to include this first

# There is no reason to compile more than two SoftDevice API versions
# The Python module only supports one SoftDevice API
# version for NRF51 and one for NRF52
set(SD_API_VERS "2;5")

# SWIG
find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

# nrf-ble-driver
find_package(nrf-ble-driver CONFIG REQUIRED)

message(STATUS "Found Python ${PYTHON_VERSION_STRING} in directory ${PYTHON_EXECUTABLE}")
message(STATUS "Linking towards Python library ${PYTHON_LIBRARY}")

# PYTHON_INCLUDE_DIR provided by scikit-build
include_directories(${PYTHON_INCLUDE_DIR})

foreach(SD_API_VER ${SD_API_VERS})
    set(PYTHON_MODULE_${SD_API_VER} nrf_ble_driver_sd_v${SD_API_VER})
endforeach()

set(SWIG_I_FILE ${CMAKE_CURRENT_LIST_DIR}/swig/pc_ble_driver.i.in)

# Use release lib of Python even when building with DEBUG
add_definitions(-DSWIG_PYTHON_INTERPRETER_NO_DEBUG -DHAVE_ROUND=1)

# Avoid warning on Windows
if(WIN32)
    add_definitions(-DHAVE_ROUND)
endif()

# Copy .i file into N variant files
foreach(SD_API_VER ${SD_API_VERS})
    # Copy SWIG-generated wrapper
    set(SWIG_I_FILE_${SD_API_VER} ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE_${SD_API_VER}}.i)
    set(SWIG_MODULE_NAME ${PYTHON_MODULE_${SD_API_VER}})
    configure_file(${SWIG_I_FILE} ${SWIG_I_FILE_${SD_API_VER}})
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} PROPERTY CPLUSPLUS OFF)
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} PROPERTY INCLUDE_DIRECTORIES ${nrf-ble-driver_SD_API_V${SD_API_VER}_INCLUDE_DIR})
    set_property(SOURCE  ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-threads")
    set_property(SOURCE  ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-DPC_BLE_DRIVER_STATIC")
endforeach()

foreach(SD_API_VER ${SD_API_VERS})
    set(SWIG_C_SRC_FILES_${SD_API_VER} ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE_${SD_API_VER}}PYTHON_wrap.c)
    set_source_files_properties(SWIG_C_SRC_FILES_${SD_API_VER} PROPERTIES LANGUAGE CXX)

    #set(CMAKE_SWIG_FLAGS "-I${nrf-ble-driver_${SD_API_VER}_INCLUDE_DIR}")
    string(REGEX MATCH "[0-9]+$" _SD_API_VER_NUM "${SD_API_VER}")
    set(SD_API_VER_COMPILER_DEF_NUM "-D${SD_API_VER_COMPILER_DEF}=${_SD_API_VER_NUM}")
    #set(CMAKE_SWIG_FLAGS ${CMAKE_SWIG_FLAGS} "${SD_API_VER_COMPILER_DEF_NUM}")

    message("Module name: ${PYTHON_MODULE_${SD_API_VER}}")

    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} PROPERTY INCLUDE_DIRECTORIES ${nrf-ble-driver_SD_API_V${SD_API_VER}_INCLUDE_DIR})

    swig_add_library(
        ${PYTHON_MODULE_${SD_API_VER}}
        TYPE SHARED
        LANGUAGE python
        SOURCES ${SWIG_I_FILE_${SD_API_VER}}
    )

    #get_target_property(include_dir nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_shared INTERFACE_INCLUDE_DIRECTORIES)

    #target_include_directories(${PYTHON_MODULE_${SD_API_VER}} PRIVATE ${include_dir})
endforeach()

# These are the files required for the pc_ble_driver Python module:

# Windows
# pc_ble_driver_<variant>.py
# _pc_ble_driver_<variant>.pyd
# pc_ble_driver_<variant>_shared.dll

# Linux
# pc_ble_driver_<variant>.py
# _pc_ble_driver_<variant>.so
# libpc_ble_driver_<variant>_shared.so

# macOS / OS X
# pc_ble_driver_<variant>.py
# _pc_ble_driver_<variant>.so
# libpc_ble_driver_<variant>_shared.dylib

foreach(SD_API_VER ${SD_API_VERS})
    target_link_libraries(${PYTHON_MODULE_${SD_API_VER}} PRIVATE nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_shared ${PYTHON_LIBRARY})
endforeach()

set(PY_PACKAGE_DIR ${CMAKE_CURRENT_LIST_DIR})
set(PY_MODULE_DIR ${PY_PACKAGE_DIR}/pc_ble_driver_py)
set(PY_MODULE_HEX_DIR ${PY_MODULE_DIR}/hex)

if(WIN32)
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/win/x86_${ARCH_BITS})
    set(SWIG_WRAPPER_SHARED_LIB_EXT pyd)
elseif(APPLE)
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/macos_osx)
    set(SWIG_WRAPPER_SHARED_LIB_EXT so)
else()
    set(PY_MODULE_SHARED_LIB_DIR ${PY_MODULE_DIR}/lib/linux/x86_${ARCH_BITS})
    set(SWIG_WRAPPER_SHARED_LIB_EXT so)
endif()

set(PY_MODULE_BUILD_INFO build_info.txt)
set(PY_MODULE_BUILD_INFO_PRE_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${PY_MODULE_BUILD_INFO})
set(PY_MODULE_BUILD_INFO_POST_PATH ${PY_MODULE_SHARED_LIB_DIR}/${PY_MODULE_BUILD_INFO})

foreach(SD_API_VER ${SD_API_VERS})
    set(SWIG_WRAPPER_${SD_API_VER}_PY_FILE ${PYTHON_MODULE_${SD_API_VER}}.py)
    set(SWIG_WRAPPER_${SD_API_VER}_PY_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${SWIG_WRAPPER_${SD_API_VER}_PY_FILE})

    set(SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_FILE _${PYTHON_MODULE_${SD_API_VER}}.${SWIG_WRAPPER_SHARED_LIB_EXT})
    set(SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_FILE})

    set(PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_FILE ${CMAKE_SHARED_LIBRARY_PREFIX}${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB}${CMAKE_SHARED_LIBRARY_SUFFIX})
    set(PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_FILE})

    # Copy SWIG-generated .py wrapper
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy ${SWIG_WRAPPER_${SD_API_VER}_PY_PATH} ${PY_MODULE_SHARED_LIB_DIR}
    )

    # Copy SWIG wrapper lib
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy ${SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
    )

    # Copy nrf-ble-driver shared library
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy ${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
    )

    # Copy .hex files
    #string(TOLOWER ${SD_API_VER} HEX_DIR)
    #add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
    #    COMMAND ${CMAKE_COMMAND} -E copy_directory ${PC_BLE_DRIVER_HEX_DIR}/${HEX_DIR} ${PY_MODULE_HEX_DIR}/${HEX_DIR})
endforeach()

foreach(SD_API_VER ${SD_API_VERS})
    install(
        TARGETS ${PYTHON_MODULE_${SD_API_VER}}
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
    )
endforeach()

# Generate build information file
set(BUILD_INFO "Build information:\n")
string(CONCAT BUILD_INFO ${BUILD_INFO} ${BUILD_MD_STRING} ) 
string(CONCAT BUILD_INFO ${BUILD_INFO} "* SWIG version: " ${SWIG_VERSION} "\n") 
string(CONCAT BUILD_INFO ${BUILD_INFO} "* Pyhon version: " ${PYTHON_VERSION_STRING} "\n") 
string(CONCAT BUILD_INFO ${BUILD_INFO} "* Pyhon libs: " ${PYTHON_LIBRARY} "\n") 
string(CONCAT BUILD_INFO ${BUILD_INFO} "* Git repo: " ${PROJECT_NAME} "\n") 
string(CONCAT BUILD_INFO ${BUILD_INFO} "** Git revision: " ${PY_GIT_COMMIT} "\n") 
string(CONCAT BUILD_INFO ${BUILD_INFO} "** Git branch: " ${PY_GIT_BRANCH} "\n") 

file(WRITE ${PY_MODULE_BUILD_INFO_PRE_PATH} ${BUILD_INFO})
