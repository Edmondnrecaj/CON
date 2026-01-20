cmake_minimum_required(VERSION 3.10)

# Setup the default build type to Debug and configure default compiler flags.
# (see https://blog.kitware.com/cmake-and-the-default-build-type/)
set(default_build_type Debug)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to '${default_build_type}' as none was specified.")
    set(CMAKE_BUILD_TYPE ${default_build_type} CACHE STRING "Choose the type of build." FORCE)
    # Set the possible values of build type for cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS Debug Release MinSizeRel RelWithDebInfo)
endif()

project(pinger LANGUAGES CXX)
enable_testing()

# Setup default compiler flags if they have not been set already.
if(NOT CMAKE_CXX_FLAGS AND (CMAKE_CXX_COMPILER_ID STREQUAL Clang OR CMAKE_CXX_COMPILER_ID STREQUAL GNU))
set(CMAKE_CXX_FLAGS "-fsanitize=address -fstack-protector-all -Wall -Wextra"
    CACHE STRING "Flags used by the compiler during all build types." FORCE)
endif()

# Add custom cmake modules to module path.
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})
include(testCoverage)

# Setup the default language standard.
set(CMAKE_CXX_STANDARD 14 CACHE STRING "Default value for CXX_STANDARD property of targets.")
set(CMAKE_CXX_EXTENSIONS OFF CACHE BOOL "Default value for CXX_EXTENSIONS property of targets.")
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Generate a compile_commands.json for tooling if possible.
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Move the built executables to the binary root directory.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")

add_subdirectory(src)
add_subdirectory(tests)
