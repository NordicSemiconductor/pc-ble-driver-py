cmake_minimum_required(VERSION 2.8.12)

# Name of the project
project (pc-ble-driver-py)

# All projects depending on pc-ble-driver need to include this first
include(pc-ble-driver/cmake/pc-ble-driver.cmake)
add_subdirectory(pc-ble-driver)

# Include folders
include_directories(${PC_BLE_DRIVER_INCLUDE_DIR})

# This line will tell CMake that we're building a shared library
# named after the project's name
#add_library(${PROJECT_NAME} SHARED src/empty.cpp pc-ble-driver)

add_library(${PROJECT_NAME} SHARED $<TARGET_OBJECTS:pc-ble-driver-obj>)

# Essential library files to link to a node addon,
# you should add this line in every CMake.js based project.
target_link_libraries(${PROJECT_NAME} PRIVATE ${Boost_LIBRARIES})
