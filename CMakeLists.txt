cmake_minimum_required(VERSION 3.13)

# Name of the project
project (pc-ble-driver-py)

set(PC_BLE_DRIVER_PY_OUTDIR ${CMAKE_BINARY_DIR}/outdir)

#set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
#set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
#set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PC_BLE_DRIVER_PY_OUTDIR})
set(CMAKE_SWIG_OUTDIR ${PC_BLE_DRIVER_PY_OUTDIR})

function(determine_arch_bits DETECTED_ARCH_BITS)
    math(EXPR COMPILER_ARCH_BITS "8*${CMAKE_SIZEOF_VOID_P}")
    # Default to compiler architecture
    set(ARCH_BITS ${COMPILER_ARCH_BITS})

    SET(ARCH not_set CACHE STRING "Architecture (x86_32 or x86_64)")
    string(TOLOWER "${ARCH}" ARCH)

    if(${ARCH} STREQUAL not_set)
        message(STATUS "Architecture not set, using native ${ARCH_BITS}-bit toolchain.")
    else()
        if(MSVC)
            message(FATAL_ERROR "ARCH not available with MSVC. Use  -G \"Visual Studio XX <Win64>\" instead.")
        elseif(APPLE)
            message(FATAL_ERROR "ARCH not available on macOS / OS X. Universal 32 and 64-bit binaries will be built.")
        endif()
        if(${ARCH} STREQUAL x86_32)
            set(ARCH_BITS 32)
        elseif(${ARCH} STREQUAL x86_64)
            set(ARCH_BITS 64)
        else()
            message(FATAL_ERROR "Invalid architecture: ARCH=${ARCH}.")
        endif()
        message(STATUS "Building ${ARCH_BITS}-bit targets with ${COMPILER_ARCH_BITS}-bit toolchain.")
    endif()

    set(${DETECTED_ARCH_BITS} ${ARCH_BITS} PARENT_SCOPE)
endfunction()

determine_arch_bits(ARCH)

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

if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(ARCH_BITS 64)
else()
    set(ARCH_BITS 32)
endif()

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
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-threads")
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-DPC_BLE_DRIVER_STATIC")
endforeach()

if(WIN32)
    execute_process(
        COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_LIST_DIR}/swig/win32/vc90-compat/stdint.h ${PC_BLE_DRIVER_PY_OUTDIR}
        RESULT_VARIABLE result
    )

    if(NOT (result EQUAL 0))
        message(FATAL_ERROR "Not able to copy stdint.h compatibility file for Microsoft VC90")
    endif()
endif()

foreach(SD_API_VER ${SD_API_VERS})
    set(SWIG_C_SRC_FILES_${SD_API_VER} ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE_${SD_API_VER}}PYTHON_wrap.c)
    set_source_files_properties(SWIG_C_SRC_FILES_${SD_API_VER} PROPERTIES LANGUAGE CXX)

    #set(CMAKE_SWIG_FLAGS "-I${nrf-ble-driver_${SD_API_VER}_INCLUDE_DIR}")
    string(REGEX MATCH "[0-9]+$" _SD_API_VER_NUM "${SD_API_VER}")
    set(SD_API_VER_COMPILER_DEF_NUM "-D${SD_API_VER_COMPILER_DEF}=${_SD_API_VER_NUM}")
    #set(CMAKE_SWIG_FLAGS ${CMAKE_SWIG_FLAGS} "${SD_API_VER_COMPILER_DEF_NUM}")

    message("Module name: ${PYTHON_MODULE_${SD_API_VER}}")

    set_property(
        SOURCE ${SWIG_I_FILE_${SD_API_VER}}
        PROPERTY INCLUDE_DIRECTORIES ${nrf-ble-driver_SD_API_V${SD_API_VER}_INCLUDE_DIR} ${PC_BLE_DRIVER_PY_OUTDIR}
    )

    swig_add_library(
        ${PYTHON_MODULE_${SD_API_VER}}
        TYPE SHARED
        LANGUAGE python
        SOURCES ${SWIG_I_FILE_${SD_API_VER}}
    )

    target_include_directories(${PYTHON_MODULE_${SD_API_VER}} PRIVATE ${PC_BLE_DRIVER_PY_OUTDIR})
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

    #set(SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_FILE _${PYTHON_MODULE_${SD_API_VER}}.${SWIG_WRAPPER_SHARED_LIB_EXT})
    #set(SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_FILE})
    #get_target_property(PYTHON_MODULE_PATH ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} LOCATION)

    set(PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_FILE ${CMAKE_SHARED_LIBRARY_PREFIX}${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB}${CMAKE_SHARED_LIBRARY_SUFFIX})
    set(PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_PATH ${PC_BLE_DRIVER_PY_OUTDIR}/${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_FILE})

    # Copy SWIG-generated .py wrapper
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy ${SWIG_WRAPPER_${SD_API_VER}_PY_PATH} ${PY_MODULE_SHARED_LIB_DIR}
    )

    set(x "$<$<TARGET_FILE:${PYTHON_MODULE_${SD_API_VER}}>>")
    message(FATAL_ERROR "TARGET: ${x}")

    # Copy SWIG wrapper lib
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
    #    COMMAND ${CMAKE_COMMAND} -E copy ${SWIG_WRAPPER_${SD_API_VER}_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
        COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:${PYTHON_MODULE_${SD_API_VER}}> ${PY_MODULE_SHARED_LIB_DIR}
    )

    # Copy nrf-ble-driver shared library
    get_target_property(NRF_BLE_DRIVER_PATH nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_shared LOCATION)
    add_custom_command(TARGET ${SWIG_MODULE_${PYTHON_MODULE_${SD_API_VER}}_REAL_NAME} POST_BUILD
        #COMMAND ${CMAKE_COMMAND} -E copy ${PC_BLE_DRIVER_${SD_API_VER}_SHARED_LIB_PATH} ${PY_MODULE_SHARED_LIB_DIR}
        COMMAND ${CMAKE_COMMAND} -E copy ${NRF_BLE_DRIVER_PATH} ${PY_MODULE_SHARED_LIB_DIR}
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
