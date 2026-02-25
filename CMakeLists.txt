cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED ENV{IDF_PATH})
    message(FATAL_ERROR "Set IDF_PATH to the path of esp-idf repo")
endif()
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Set true if you want to use Matter
set(ESP_MATTER_ENABLED false)
if (ESP_MATTER_ENABLED)
    if(NOT DEFINED ENV{ESP_MATTER_PATH})
        message(
            FATAL_ERROR "Set ESP_MATTER_PATH to the path of esp-matter repo")
    endif()

    set(ESP_MATTER_PATH $ENV{ESP_MATTER_PATH})
    set(MATTER_SDK_PATH ${ESP_MATTER_PATH}/connectedhomeip/connectedhomeip)

    set(EXTRA_COMPONENT_DIRS
        "${MATTER_SDK_PATH}/config/esp32/components"
        "${ESP_MATTER_PATH}/components"
        ${extra_components_dirs_append})
endif()

project(esp-idf-project)

idf_build_set_property(CXX_COMPILE_OPTIONS "-Wno-overloaded-virtual" APPEND)
idf_build_set_property(COMPILE_OPTIONS "-Os" APPEND)

if (ESP_MATTER_ENABLED)
    idf_build_set_property(CXX_COMPILE_OPTIONS "-DCHIP_HAVE_CONFIG_H" APPEND)

    idf_build_get_property(all_components BUILD_COMPONENTS)
    foreach(comp ${all_components})
        idf_component_get_property(comp_lib ${comp} COMPONENT_LIB)
        idf_component_get_property(comp_dir ${comp} COMPONENT_DIR)

        if (comp_dir MATCHES "^${ESP_MATTER_PATH}(/|$)")
            get_target_property(_type ${comp_lib} TYPE)
            set(_scope PRIVATE)
            if (_type STREQUAL "INTERFACE_LIBRARY")
                set(_scope INTERFACE)
            endif()

            target_compile_options(${comp_lib} ${_scope}
                $<$<COMPILE_LANGUAGE:CXX>:-std=gnu++17;-w>)
        endif()
    endforeach()
endif()

if(IDF_TARGET_ARCH STREQUAL "riscv")
    idf_build_set_property(
        COMPILE_OPTIONS "-Wno-format-nonliteral;-Wno-format-security" APPEND)
endif()
