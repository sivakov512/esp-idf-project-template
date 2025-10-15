function(add_unity_test NAME)
    cmake_parse_arguments(TEST "" "" "SRCS;LIBS;HEADERS" ${ARGN})

    add_executable(${NAME} ${TEST_SRCS} ${TEST_HEADERS})
    target_link_libraries(${NAME} PRIVATE unity ${TEST_LIBS})

    set_target_properties(${NAME} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    )

    add_test(NAME ${NAME} COMMAND ${NAME})
endfunction()
