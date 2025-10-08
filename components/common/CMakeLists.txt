idf_component_register(
    SRCS ""
    INCLUDE_DIRS "include"
)

set(LIB_NAME common)

add_subdirectory(
    ${EXT_LIBS_DIR}/${LIB_NAME} ${CMAKE_BINARY_DIR}/ext_libs/${LIB_NAME}
)
target_link_libraries(${COMPONENT_LIB} INTERFACE ${LIB_NAME})
