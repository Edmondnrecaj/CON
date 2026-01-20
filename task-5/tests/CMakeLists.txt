add_test(NAME arp.req.reply COMMAND ${CMAKE_COMMAND}
    -D "PROGRAM:STRING=$<TARGET_FILE:pinger>"
    -D "ARGS:STRING=--respond;11:22:33:44:55:66;192.168.56.101"
    -D "INPUT_FILE:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req.pcapng;--csv"
    -D "OUTPUT_FILE:STRING=arp.req.out.cap"
    -D "COMPARE_TOOL:STRING=diff;--strip-trailing-cr"
    -D "PRE_DELETE_COMPARE_FILES:BOOL=true"
    -D "COMPARE_FILES:STRING=arp.req.csv"
    -D "REFERENCE_FILES:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req.reply.csv"
    -D "RETURN_VALUE:STRING=COMBINED"
    -P "${CMAKE_SOURCE_DIR}/cmake/scripts/run.cmake"
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

add_test(NAME arp.req.noreply COMMAND ${CMAKE_COMMAND}
    -D "PROGRAM:STRING=$<TARGET_FILE:pinger>"
    -D "ARGS:STRING=--respond;11:22:33:44:55:66;192.168.56.102"
    -D "INPUT_FILE:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req.pcapng;--csv"
    -D "OUTPUT_FILE:STRING=arp.req.noreply.out.cap"
    -D "COMPARE_TOOL:STRING=diff;--strip-trailing-cr"
    -D "PRE_DELETE_COMPARE_FILES:BOOL=true"
    -D "COMPARE_FILES:STRING=arp.req.noreply.csv"
    -D "REFERENCE_FILES:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req.noreply.csv"
    -D "RETURN_VALUE:STRING=COMBINED"
    -P "${CMAKE_SOURCE_DIR}/cmake/scripts/run.cmake"
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

add_test(NAME arp.req+3xicmp_echo.reply COMMAND ${CMAKE_COMMAND}
    -D "PROGRAM:STRING=$<TARGET_FILE:pinger>"
    -D "ARGS:STRING=--respond;11:22:33:44:55:66;192.168.56.101"
    -D "INPUT_FILE:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req+3xicmp_echo.pcapng;--csv"
    -D "OUTPUT_FILE:STRING=arp.req+3xicmp_echo.out.cap"
    -D "COMPARE_TOOL:STRING=diff;--strip-trailing-cr"
    -D "PRE_DELETE_COMPARE_FILES:BOOL=true"
    -D "COMPARE_FILES:STRING=arp.req+3xicmp_echo.csv"
    -D "REFERENCE_FILES:STRING=${CMAKE_CURRENT_SOURCE_DIR}/arp.req+3xicmp_echo.reply.csv"
    -D "RETURN_VALUE:STRING=COMBINED"
    -P "${CMAKE_SOURCE_DIR}/cmake/scripts/run.cmake"
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
