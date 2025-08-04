# ESP-IDF Project Template

A clean ESP-IDF project template with pre-configured development tools and build settings.

## What's Included

- Pre-configured development tools (clang-format, clang-tidy, clangd)
- Google C++ style guide compliance
- Matter support (commented, ready to uncomment)
- RISC-V compatibility settings
- Optimized build settings (`-Os`)

## Prerequisites & Resources

- [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html) v5.4+ (tested on 5.4, may work on earlier versions)
- [ESP-Matter](https://github.com/espressif/esp-matter) - for Matter/Thread support
- [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) - coding standards
- [clang-format](https://clang.llvm.org/docs/ClangFormat.html), [clang-tidy](https://clang.llvm.org/extra/clang-tidy/), [clangd](https://clangd.llvm.org/) - development tools

## Setup

Change project name in `CMakeLists.txt`:
```cmake
project(your-project-name)
```

For build, flash, and monitor instructions refer to ESP-IDF documentation.

## Configuration

### C++ Support

To enable C++20 support:

1. Uncomment in `CMakeLists.txt`:
   ```cmake
   idf_build_set_property(
       CXX_COMPILE_OPTIONS "-std=gnu++20;-Os;-Wno-overloaded-virtual" APPEND)
   ```

2. Uncomment in `.clangd`:
   ```yaml
   Add:
     - -std=gnu++20
   ```

### Matter/Thread Support

To enable Matter support:

1. Set up ESP-Matter and export `ESP_MATTER_PATH`
2. Uncomment all Matter-related sections in `CMakeLists.txt`

### RISC-V Targets

For ESP32-C3, ESP32-C6, etc., uncomment the RISC-V compiler flags in `CMakeLists.txt`:
```cmake
idf_build_set_property(
    COMPILE_OPTIONS "-Wno-format-nonliteral;-Wno-format-security" APPEND)
```
