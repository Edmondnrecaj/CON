# This script adds clang-format support to the build system (format target).
#
# Files which should be formated have to be added using add_file_to_format
# function.
#
# Processed variables:
#   CLANGFORMAT_STYLE.............style which should be applied (default: file)
#                                 (cache variable)
#
# Provided targets:
#   format........................reformat the specified source files
#
# Provided macros/functions:
#   add_file_to_format............specifiy files which should be formatted
#

# Search for the clang-format executable and export the used style to the cache
# to enable modification.
find_program(CLANGFORMAT_EXECUTABLE NAMES "clang-format")
set(CLANGFORMAT_STYLE "file" CACHE STRING "Argument for the style parameter of clang-format.")
mark_as_advanced(CLANGFORMAT_EXECUTABLE CLANGFORMAT_STYLE)

# Abort further processing if function has already been defined or no
# clang-format executable is available.
if(COMMAND add_file_to_format)
  return()
elseif(NOT CLANGFORMAT_EXECUTABLE)
  message(STATUS "clang-format couldn't be found. Source code formatting will not be available.")
  function(add_file_to_format)
  endfunction()
  return()
endif()

function(add_file_to_format)
  if(NOT CLANGFORMAT_EXECUTABLE)
    return()
  endif()
  if(NOT TARGET format)
    add_custom_target(format)
  endif()

  foreach(absfile ${ARGN})
    if(NOT IS_ABSOLUTE "${absfile}")
      set(absfile "${CMAKE_CURRENT_SOURCE_DIR}/${absfile}")
    endif()

    # create a target name which is unique for all files in the project
    file(RELATIVE_PATH target "${PROJECT_SOURCE_DIR}" "${absfile}")
    string(REGEX REPLACE "/" "_" target "_format_${target}")

    # straight forward target which formats all files every time
    #add_custom_target("${target}" COMMAND "${CLANGFORMAT_EXECUTABLE}" "-i" "-style=${CLANGFORMAT_STYLE}" "${absfile}"
    #                    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    #                    COMMENT "Formatting \"${absfile}\"." VERBATIM)

    # cache the format runs and only format the changed ones
    add_custom_target(${target} DEPENDS "${PROJECT_BINARY_DIR}/_clangformat_cache/${target}")
    add_custom_command(OUTPUT "${PROJECT_BINARY_DIR}/_clangformat_cache/${target}"
                        COMMAND "${CLANGFORMAT_EXECUTABLE}" -i "-style=${CLANGFORMAT_STYLE}" "${absfile}"
                        COMMAND "${CMAKE_COMMAND}" -E make_directory "${PROJECT_BINARY_DIR}/_clangformat_cache"
                        COMMAND "${CMAKE_COMMAND}" -E touch "${PROJECT_BINARY_DIR}/_clangformat_cache/${target}"
                        DEPENDS "${absfile}"
                        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                        COMMENT "Formatting \"${absfile}\"." VERBATIM)

    add_dependencies(format ${target})
  endforeach()
endfunction()
