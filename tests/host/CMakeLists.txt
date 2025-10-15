cmake_minimum_required(VERSION 3.16)

set(ROOT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../)

project(project_tests C)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)
include(AddUnityTest)

include(FetchContent)

FetchContent_Declare(
    Unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG        v2.6.1
)
FetchContent_MakeAvailable(Unity)

if(NOT TARGET unity)
    add_library(unity STATIC ${Unity_SOURCE_DIR}/src/unity.c)
    target_include_directories(unity PUBLIC ${Unity_SOURCE_DIR}/src)
endif()

enable_testing()

set(MANAGED_COMPONENTS embedlibs)
foreach(DEP ${MANAGED_COMPONENTS})
    add_subdirectory(
        ${ROOT_DIR}/managed_components/${DEP}
        ${CMAKE_BINARY_DIR}/managed_components/${DEP}
    )
endforeach()

# Add components compatible for host testing here
# Before adding library here, create directory named tests inside and write
# CMakeLists.txt with content like this:
# add_unity_test(component_name_tests
#     SRCS test_file.c
#     LIBS component_name
# )
set(LIBS2TEST )
foreach(LIB ${LIBS2TEST})
    add_subdirectory(
        ${ROOT_DIR}/components/${LIB}
        ${CMAKE_BINARY_DIR}/components/${LIB}
    )
    add_subdirectory(
        ${ROOT_DIR}/components/${LIB}/tests
        ${CMAKE_BINARY_DIR}/components/${LIB}/tests
    )
endforeach()
