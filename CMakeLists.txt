# The following lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

# Uncomment to use Matter
# if(NOT DEFINED ENV{ESP_MATTER_PATH})
#     message(FATAL_ERROR "Set ESP_MATTER_PATH to the path of esp-matter repo")
# endif(NOT DEFINED ENV{ESP_MATTER_PATH})
# set(ESP_MATTER_PATH $ENV{ESP_MATTER_PATH})
# set(MATTER_SDK_PATH ${ESP_MATTER_PATH}/connectedhomeip/connectedhomeip)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Path to directory with clean esp-independent libraries
set(EXT_LIBS_DIR "${CMAKE_CURRENT_LIST_DIR}/libs")


# Uncomment to use Matter
# set(EXTRA_COMPONENT_DIRS
#     "${MATTER_SDK_PATH}/config/esp32/components"
#     "${ESP_MATTER_PATH}/components"
#     ${extra_components_dirs_append})

project(esp-idf-project)

idf_build_set_property(
    CXX_COMPILE_OPTIONS "-std=gnu++20;-Os;-Wno-overloaded-virtual" APPEND)

# Uncomment to use Matter
# idf_build_set_property(CXX_COMPILE_OPTIONS "-DCHIP_HAVE_CONFIG_H" APPEND)

# Uncomment for RISC-V chips
# Reason is that for RISCV chips, project_include.cmake sets -Wno-format,
# but does not clear various flags that depend on -Wformat
# idf_build_set_property(
#     COMPILE_OPTIONS "-Wno-format-nonliteral;-Wno-format-security" APPEND)

idf_build_set_property(C_COMPILE_OPTIONS "-Os" APPEND)
