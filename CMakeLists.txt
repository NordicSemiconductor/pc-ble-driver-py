cmake_minimum_required(VERSION 3.13)

if(DEFINED ENV{VCPKG_ROOT} AND NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        CACHE STRING "")
endif()
# Name of the project
project (pc-ble-driver-py)
#set(CMAKE_FIND_DEBUG_MODE 1)

message("CMAKE executable path ${CMAKE_COMMAND}")
message("CMake Generator name: ${CMAKE_GENERATOR}")
message("cmake generator path ${CMAKE_MAKE_PROGRAM}")
message("CMAKE_MODULE_PATH before most other commands : ${CMAKE_MODULE_PATH}")
message("The include directories are (before PythonExtensions): ${PYTHON_INCLUDE_DIR}")
message("Start of finding python extension")
find_package(PythonExtensions REQUIRED)
message("end of finding python extension")
message("The include directories are (after PythonExtensions): ${PYTHON_INCLUDE_DIR}")

message("PythonExtension parameters")
message("PYTHON_PREFIX                    :   ${PYTHON_PREFIX}                     ")
message("PYTHON_SITE_PACKAGES_DIR         :   ${PYTHON_SITE_PACKAGES_DIR}          ")
message("PYTHON_RELATIVE_SITE_PACKAGES_DIR:   ${PYTHON_RELATIVE_SITE_PACKAGES_DIR} ")
message("PYTHON_SEPARATOR                 :   ${PYTHON_SEPARATOR}                  ")
message("PYTHON_PATH_SEPARATOR            :   ${PYTHON_PATH_SEPARATOR}             ")
message("PYTHON_EXTENSION_MODULE_SUFFIX   :   ${PYTHON_EXTENSION_MODULE_SUFFIX}    ")

message("CMAKE_MODULE_PATH afterch most other commands : ${CMAKE_MODULE_PATH}")

if(WIN32)
    message("Bulding a win32 program")
else()
    message("Bulding a win64 program")
endif()
if(WIN32)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -D_hypot=hypot")
endif()

set(PC_BLE_DRIVER_PY_OUTDIR ${CMAKE_BINARY_DIR}/outdir)
set(NRF_BLE_DRIVER_VERSION "4.1.4")

# There is no reason to compile more than two SoftDevice API versions
# The Python module only supports one SoftDevice API
# version for NRF51 and one for NRF52
set(SD_API_VERS "2;5")

# SWIG
find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

# nrf-ble-driver
find_package(nrf-ble-driver ${NRF_BLE_DRIVER_VERSION} EXACT CONFIG REQUIRED)

# PYTHON_INCLUDE_DIR provided by scikit-build
include_directories(${PYTHON_INCLUDE_DIR})
message("The include directories are: ${PYTHON_INCLUDE_DIR}")

set(SWIG_I_FILE ${CMAKE_CURRENT_LIST_DIR}/swig/pc_ble_driver.i.in)

# Use release lib of Python even when building with DEBUG
add_definitions(-DSWIG_PYTHON_INTERPRETER_NO_DEBUG)

# Avoid warning on Windows
if(WIN32)
    add_definitions(-DHAVE_ROUND)
endif()

# Copy .i file into N variant files
foreach(SD_API_VER ${SD_API_VERS})
    set(PYTHON_MODULE_${SD_API_VER} nrf_ble_driver_sd_api_v${SD_API_VER})
    # Copy SWIG-generated wrapper
    set(SWIG_I_FILE_${SD_API_VER} ${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE_${SD_API_VER}}.i)
    set(SWIG_MODULE_NAME ${PYTHON_MODULE_${SD_API_VER}})
    configure_file(${SWIG_I_FILE} ${SWIG_I_FILE_${SD_API_VER}})
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-threads")
    set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-Wall")
    # Builtin is not supported in the customized wrappers for callbacks yet
    # set_property(SOURCE ${SWIG_I_FILE_${SD_API_VER}} APPEND PROPERTY SWIG_FLAGS "-builtin")
endforeach()

set(NRF_BLE_DRIVER_LINKAGE_TYPE "static")

if(WIN32)
    set(NRF_BLE_DRIVER_LINKAGE_TYPE "shared")
endif()

foreach(SD_API_VER ${SD_API_VERS})
    set_property(
        SOURCE ${SWIG_I_FILE_${SD_API_VER}}
        # C++ must be off since SWIG C++ parser does not handle nested structs/classes
        # Warning 312. Unnamed nested class not currently supported (ignored)
        PROPERTY CPLUSPLUS OFF
    )

    set_property(
        SOURCE ${SWIG_I_FILE_${SD_API_VER}}
        PROPERTY INCLUDE_DIRECTORIES ${nrf-ble-driver_SD_API_V${SD_API_VER}_INCLUDE_DIR} ${PC_BLE_DRIVER_PY_OUTDIR}
    )

    set_property(
        SOURCE ${SWIG_I_FILE_${SD_API_VER}}
        PROPERTY COMPILE_DEFINITIONS "NRF_SD_BLE_API_VERSION=${SD_API_VER}" "SUPPRESS_INLINE_IMPLEMENTATION" "PC_BLE_DRIVER_STATIC"
    )

    swig_add_library(
        ${PYTHON_MODULE_${SD_API_VER}}
        TYPE SHARED
        LANGUAGE python
        SOURCES ${SWIG_I_FILE_${SD_API_VER}}
        OUTPUT_DIR ${PC_BLE_DRIVER_PY_OUTDIR}
    )

    set_property(TARGET ${PYTHON_MODULE_${SD_API_VER}} PROPERTY CXX_STANDARD 14)
    set_property(TARGET ${PYTHON_MODULE_${SD_API_VER}} PROPERTY CXX_STANDARD_REQUIRED TRUE)

    set_source_files_properties(${PC_BLE_DRIVER_PY_OUTDIR}/${PYTHON_MODULE_${SD_API_VER}}PYTHON_wrap.c PROPERTIES LANGUAGE CXX)

    if(MSFT_NON_STANDARD_COMPILER)
        target_include_directories(${PYTHON_MODULE_${SD_API_VER}} PRIVATE ${PC_BLE_DRIVER_PY_OUTDIR})
    endif()

    set(LINK_LIBRARIES nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_${NRF_BLE_DRIVER_LINKAGE_TYPE})
    if (WIN32 OR APPLE)
        set(LINK_LIBRARIES ${LINK_LIBRARIES} ${PYTHON_LIBRARY})
        message("Python libbrary is : ${PYTHON_LIBRARY}")
        message("link libraries are: ${LINK_LIBRARIES}")
    endif()

    message(STATUS "LINK_LIBRARIES are not ${LINK_LIBRARIES}")

    target_link_libraries(${PYTHON_MODULE_${SD_API_VER}} PRIVATE ${LINK_LIBRARIES})
    target_compile_definitions(${PYTHON_MODULE_${SD_API_VER}} PRIVATE NRF_SD_BLE_API_VERSION=${SD_API_VER})

    get_target_property(CONNECTIVITY_SD_API_V${SD_API_VER}_PATH nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_${NRF_BLE_DRIVER_LINKAGE_TYPE} INTERFACE_INCLUDE_DIRECTORIES)
    set(CONNECTIVITY_SD_API_V${SD_API_VER}_PATH ${CONNECTIVITY_SD_API_V${SD_API_VER}_PATH}/../../share/nrf-ble-driver/hex/sd_api_v${SD_API_VER})
    file(GLOB_RECURSE CONNECTIVITY_SD_API_V${SD_API_VER}_FILES "${CONNECTIVITY_SD_API_V${SD_API_VER}_PATH}/*.hex" "${CONNECTIVITY_SD_API_V${SD_API_VER}_PATH}/*.zip")

    set_property(
        TARGET ${PYTHON_MODULE_${SD_API_VER}}
        PROPERTY RESOURCE "${CONNECTIVITY_SD_API_V${SD_API_VER}_FILES}"
    )
    if(APPLE)
        set_property(TARGET ${PYTHON_MODULE_${SD_API_VER}} PROPERTY SUFFIX ".so")
    endif()
endforeach()

set(BUILD_OUTPUT_LIB_DIR "pc_ble_driver_py/lib")
set(BUILD_OUTPUT_HEX_DIR "pc_ble_driver_py/hex")

foreach(SD_API_VER ${SD_API_VERS})
    install(
        TARGETS ${PYTHON_MODULE_${SD_API_VER}}
        RUNTIME DESTINATION ${BUILD_OUTPUT_LIB_DIR}
        LIBRARY DESTINATION ${BUILD_OUTPUT_LIB_DIR}
        ARCHIVE DESTINATION ${BUILD_OUTPUT_LIB_DIR}
        RESOURCE DESTINATION "${BUILD_OUTPUT_HEX_DIR}/sd_api_v${SD_API_VER}"
    )

    install(
        FILES ${PC_BLE_DRIVER_PY_OUTDIR}/nrf_ble_driver_sd_api_v${SD_API_VER}.py
        DESTINATION ${BUILD_OUTPUT_LIB_DIR}
    )

    if(NRF_BLE_DRIVER_LINKAGE_TYPE STREQUAL "shared")
        install(
            FILES $<TARGET_FILE:nrf::nrf_ble_driver_sd_api_v${SD_API_VER}_${NRF_BLE_DRIVER_LINKAGE_TYPE}>
            DESTINATION ${BUILD_OUTPUT_LIB_DIR}
        )
    endif()
endforeach()
