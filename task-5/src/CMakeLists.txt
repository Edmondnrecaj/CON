find_package(PCAP REQUIRED)

# Glob all source files. (cmake before 3.13 lacks CONFIGURE_DEPENDS but we
# still want to use it if it is available.)
set(OPT_CONF_DEP)
if(CMAKE_VERSION VERSION_GREATER 3.13.0 OR CMAKE_VERSION VERSION_EQUAL 3.13.0)
  set(OPT_CONF_DEP CONFIGURE_DEPENDS)
endif()
file(GLOB_RECURSE sources ${OPT_CONF_DEP} *.cpp)

# Define the actual build target.
add_executable(pinger ${sources})
target_include_directories(pinger PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(pinger PUBLIC cxx_std_14)
target_link_libraries(pinger PUBLIC pcap::pcap)

# Register all source files for bulk reformatting.
include(clangformat)
file(GLOB_RECURSE headers ${OPT_CONF_DEP} *.h)
add_file_to_format(${sources} ${headers})

# Add target for granting raw network capabilities.
add_custom_target(setcap COMMAND sudo setcap cap_net_raw+ep $<TARGET_FILE:pinger>)
