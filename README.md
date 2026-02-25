# ESP-IDF Project Template

Minimal ESP-IDF project template with clean build defaults, clang tooling, and optional ESP-Matter support.

## Features

- Clean ESP-IDF CMake setup
- clang-format / clang-tidy / clangd integration
- Size-optimized builds (`-Os`)
- Optional ESP-Matter / connectedhomeip support
- Matter components forced to GNU++17
- RISC-V compatibility flags

---

## Requirements

- [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html) v5.4+
- [ESP-Matter](https://docs.espressif.com/projects/esp-matter/en/latest/esp32/developing.html#esp-matter-setup) (optional, for Matter / Thread)
- clang-format / clang-tidy / clangd (recommended)

## Setup

Rename the project in `CMakeLists.txt`:

```cmake
project(your-project-name)
```

Build and flash:

```bash
idf.py build
idf.py flash monitor
```

## C++ Standard

The template does not globally override the C++ standard.

Your project code uses the default provided by ESP-IDF/toolchain
(often shown as -std=gnu++2b, which is GNU C++23).

When Matter is enabled:

- Matter / CHIP components are compiled with -std=gnu++17
- Warnings for upstream Matter code are disabled (-w)

This avoids C++23 incompatibilities inside connectedhomeip while keeping your project on a modern standard.

## Enabling Matter

1. Set `ESP_MATTER_PATH`

2. Enable in CMakeLists.txt:

```cmake
set(ESP_MATTER_ENABLED true)
```

3. Clean and rebuild:

```bash
idf.py fullclean
idf.py build
```

## RISC-V Targets

For RISC-V chips (ESP32-C3 / C6 / H2 / etc.) additional format-related warnings are disabled:

```cmake
if(IDF_TARGET_ARCH STREQUAL "riscv")
    idf_build_set_property(
        COMPILE_OPTIONS "-Wno-format-nonliteral;-Wno-format-security" APPEND)
endif()
```

## Code Style

Clang-tidy enforces:

Naming

- C: snake_case, structs/typedefs end with \_t
- C++ types: CamelCase
- Methods: snake_case
- Class members: snake*case*
- Enum values: UPPER_CASE
- Class constants: kCamelCase
- Macros and global constants: UPPER_CASE
- Globals: g\_ prefix

Rules

- All warnings treated as errors
- Analyzer, performance, modernize, readability checks enabled
- Embedded-oriented exceptions configured where necessary

See .clang-tidy for the full configuration.
