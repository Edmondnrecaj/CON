# Executes a program, control the in and output, and compare the results to a reference.
#
# The following variables have to be defined to run this script:
#   PROGRAM.............................The program and the parameters which should be executed.
#
# The following variables can to be defined to control the behavior:
#   INPUT_FILE..........................Path to the file which is provided via stdin.
#   OUTPUT_FILE.........................Path to the file where stdout should be stored.
#   ERROR_FILE..........................Path to the file where stderr should be stored.
#
#   PRINT_INPUT_FILE....................If an INPUT_FILE is used, output it before the PROGRAM execution.
#   PRINT_OUTPUT_FILE...................If an OUTPUT_FILE is used, output it after the PROGRAM execution.
#   PRINT_ERROR_FILE....................If an ERROR_FILE is used, output it after the PROGRAM execution.
#
#   RETURN_VALUE........................Controls the return value of the script.
#    - EXECUTION........................Zero if execution returned 0, non zero otherwise (default).
#    - COMPARISON.......................Zero if comparison was successful, non zero otherwise.
#    - COMBINED.........................Zero if execution returned 0 and comparison was successful, non zero otherwise.
#    - ZERO.............................Always return zero.
#
#   COMPARE_TOOL........................Program which is used for the comparison (default: cmake -E compare_files).
#   COMPARE_FILES.......................List of files which should be compared against some reference.
#   REFERENCE_FILES.....................List of reference files.
#   PRE_DELETE_COMPARE_FILES............Delete the files which are later compared before PROGRAM execution.
#
# Example for adding a target using this script:
#  add_custom_target( foobar COMMAND "${CMAKE_COMMAND}"
#                 -D "PROGRAM:STRING=${PROGRAM}"
#                 -P "${PROJECT_SOURCE_DIR}/cmake/scripts/run.cmake")
cmake_minimum_required(VERSION 3.0.0)

#
# Validate the parameters.
#
if(NOT PROGRAM)
  message(STATUS "[RUN] The following variables have to be defined (-D) to run this script:")
  message(STATUS "[RUN]   PROGRAM.............................The program and the parameters which should be executed")
  message(SEND_ERROR "[RUN] Invalid/insufficient parameters specified!")
endif()

# Validate that a valid option for the RETURN_VALUE parameter has been specified.
set(RETURN_VALUE_OPTIONS EXECUTION COMPARISON COMBINED ZERO)
list(FIND RETURN_VALUE_OPTIONS "${RETURN_VALUE}" idx)
if(RETURN_VALUE AND idx EQUAL -1)
  message(SEND_ERROR "[RUN] Invalid option (${RETURN_VALUE}) specified as RETURN_VALUE!")
endif()
if(NOT RETURN_VALUE)
  set(RETURN_VALUE EXECUTION)
endif()

# Validate that there are as many reference as compare files.
list(LENGTH COMPARE_FILES compare_files_length)
list(LENGTH REFERENCE_FILES reference_files_length)
if(NOT compare_files_length EQUAL reference_files_length)
  message(SEND_ERROR "[RUN] Compare file count (${compare_files_length}) does not match reference file count (${reference_files_length})!")
endif()

#
# Perform pre execution steps.
#

# Delete compare files if requested.
if(PRE_DELETE_COMPARE_FILES)
  foreach(file ${COMPARE_FILES})
    message(STATUS "[RUN] Deleting \"${file}\" before executing the program")
    file(REMOVE ${file})
  endforeach()
endif()

# Display input file if desired.
if(PRINT_INPUT_FILE AND INPUT_FILE)
  file(READ "${INPUT_FILE}" input_data)
  message(STATUS "[RUN] <Begin of input file (${INPUT_FILE})>\n${input_data}")
  message(STATUS "[RUN] <End of input file (${INPUT_FILE})>")
endif()

# Generate human readable program execution string and show it.
string(REGEX REPLACE ";" " " PROGRAM_STR "${PROGRAM}")
message(STATUS "[RUN] Execution command: \"${PROGRAM_STR}\"")

#
# Execute the program.
#
execute_process(COMMAND ${PROGRAM} -i ${INPUT_FILE} ${ARGS} -o ${OUTPUT_FILE} RESULT_VARIABLE execution_result OUTPUT_VARIABLE stdout_content)
message(STATUS "[RUN] Execution return code: ${execution_result}")

list(GET COMPARE_FILES 0 comp_file)
file(WRITE "${comp_file}" "${stdout_content}")

# Display output file if desired.
if(PRINT_OUTPUT_FILE AND OUTPUT_FILE)
  file(READ "${OUTPUT_FILE}" output_data)
  message(STATUS "[RUN] <Begin of output file (${OUTPUT_FILE})>\n${output_data}")
  message(STATUS "[RUN] <End of output file (${OUTPUT_FILE})>")
endif()

# Display error file if desired.
if(PRINT_ERROR_FILE AND ERROR_FILE)
  file(READ "${ERROR_FILE}" error_data)
  message(STATUS "[RUN] <Begin of output file (${ERROR_FILE})>\n${error_data}")
  message(STATUS "[RUN] <End of output file (${ERROR_FILE})>")
endif()

#
# Compare all result files.
#
set(compare_result "0")
if(NOT COMPARE_TOOL)
  set(COMPARE_TOOL "${CMAKE_COMMAND}" -E compare_files)
endif()
if(compare_files_length GREATER 0)
  foreach(i RANGE 1 ${compare_files_length})
    math(EXPR idx "${i}-1")
    list(GET COMPARE_FILES ${idx} comp_file)
    list(GET REFERENCE_FILES ${idx} ref_file)

    message(STATUS "[RUN] Comparing \"${ref_file}\" with \"${comp_file}\"")

    # Generate human readable comparison string and show it.
    string(REGEX REPLACE ";" " " PROGRAM_STR "${COMPARE_TOOL};${ref_file};${comp_file}")
    message(STATUS "[RUN] Comparision command: \"${PROGRAM_STR}\"")

    execute_process(COMMAND ${COMPARE_TOOL} ${ref_file} ${comp_file}
                    RESULT_VARIABLE result)
    message(STATUS "[RUN] Comparision return code: ${result}")

    # Capture the first error.
    if(NOT compare_result AND result)
      set(compare_result ${result})
    endif()
  endforeach()
endif()

if((RETURN_VALUE STREQUAL "EXECUTION" AND execution_result) OR
   (RETURN_VALUE STREQUAL "COMPARISON" AND compare_result) OR
   (RETURN_VALUE STREQUAL "COMBINED" AND (compare_result OR execution_result)))
  message(SEND_ERROR "[RUN] Run failed!")
endif()
