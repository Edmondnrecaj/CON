# The following variables have to be defined to run this script:
#   PROGRAM.............................The pinger program.
#   ARGS................................Arguments for the initial program call.
#   INPUT_FILE..........................Path to the file which is provided as input.
#   OUTPUT_FILE.........................Path to the file with the reply should be stored.
#   REFERENCE_FILE......................Path to the file with expected CSV output.

cmake_minimum_required(VERSION 3.0.0)

get_filename_component(CMAKE_MODULE_ROOT_DIR "${CMAKE_CURRENT_LIST_FILE}" DIRECTORY)

message(STATUS "Executing command: ${PROGRAM} -i ${INPUT_FILE} ${ARGS} -o ${OUTPUT_FILE}")
execute_process(COMMAND ${PROGRAM} -i ${INPUT_FILE} ${ARGS} -o ${OUTPUT_FILE}
                RESULT_VARIABLE execution_result)
if(execution_result)
  message(SEND_ERROR "Executing program failed!")
endif()

execute_process(COMMAND ${CMAKE_COMMAND}
                    -D "PROGRAM:STRING=${PROGRAM};-i;${OUTPUT_FILE};--csv"
                    -D "OUTPUT_FILE:STRING=${OUTPUT_FILE}.csv"
                    -D "PRE_DELETE_COMPARE_FILES:BOOL=true"
                    -D "COMPARE_FILES:STRING=${OUTPUT_FILE}.csv"
                    -D "REFERENCE_FILES:STRING=${REFERENCE_FILE}"
                    -D "RETURN_VALUE:STRING=COMBINED"
                    -P "${CMAKE_MODULE_ROOT_DIR}/run.cmake"
                RESULT_VARIABLE execution_result)
if(execution_result)
  message(SEND_ERROR "Executing program failed!")
endif()
