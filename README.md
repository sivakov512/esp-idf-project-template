# ESP-IDF Project Template

An ESP-IDF project base with clang-tidy, clangd, and CI pre-configured, host-side unit tests ready to run, and optional ESP-Matter support. Start writing firmware, not tooling config.

[![ESP Lint](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/esp-lint.yml/badge.svg)](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/esp-lint.yml)
[![Formatting](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/formatting.yml/badge.svg)](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/formatting.yml)

## What's included

- **clang-format, clang-tidy, and clangd work out of the box** — [`sanitize_compile_db.py`](sanitize_compile_db.py) strips GCC-specific flags from ESP-IDF's `compile_commands.json` and injects the correct toolchain/sysroot; works on both Xtensa and RISC-V targets
- **CI pre-configured** — GitHub Actions for static analysis and formatting; auto-selects the correct Docker image when Matter is enabled
- **Host-side unit tests** — [Unity](https://github.com/ThrowTheSwitch/Unity) via CMake `FetchContent`; test business logic without hardware
- **App structure** — `main/` entry point + `components/app/` business logic, ready to expand
- **Optional ESP-Matter** — connectedhomeip integration with C++17 pinning for Matter components

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/) | v5.4+ | Required |
| CMake | 3.16+ | For host tests |
| clang-format / clang-tidy / clangd | 18+ | Recommended |
| [ESP-Matter](https://docs.espressif.com/projects/esp-matter/en/latest/esp32/developing.html) | release_v1.5+ | Optional |

---

## Quick Start

Click **"Use this template" → "Create a new repository"** on GitHub, then clone your new repo.

Rename the project in `CMakeLists.txt`:

```cmake
project(your-project-name)
```

Build and flash:

```bash
make esp-build
make esp-flashm        # flash + open serial monitor
```

---

## Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   ├── esp-lint.yml        # clang-tidy on ESP target (auto-picks Matter image if needed)
│   │   └── formatting.yml      # clang-format check
│   └── disabled_workflows/
│       └── host-checks.yml     # host tests + lint (enable when you add testable components)
├── components/
│   └── app/                    # Main application component
│       ├── include/app.h       # app_ctx_t, app_init(), app_run()
│       ├── app.c
│       └── CMakeLists.txt
├── main/
│   ├── main.c                  # app_main() — calls app_init() then app_run(), handles errors
│   ├── idf_component.yml       # IDF component manager dependencies
│   └── CMakeLists.txt
├── tests/
│   └── host/                   # Host-side unit tests (Unity, no hardware needed)
│       ├── cmake/
│       │   └── AddUnityTest.cmake
│       └── CMakeLists.txt
├── .clang-format               # LLVM-based style, 85 col limit, 4-space indent
├── .clang-tidy                 # Static analysis rules, all warnings as errors
├── .clangd                     # LSP config — strips GCC flags for IDE compatibility
├── sanitize_compile_db.py      # Patches IDF's compile_commands.json for clang-tidy
├── sdkconfig.defaults          # IDF defaults (partition table hints)
├── CMakeLists.txt              # Top-level build
└── Makefile                    # Convenience targets for all common workflows
```

`app_main()` calls `app_init()` then `app_run()` on `app_ctx_t` and handles errors uniformly. All business logic goes in `components/app/` or new components alongside it; `main.c` stays minimal.

Dependencies pulled via IDF component manager (`main/idf_component.yml`):

| Library | Purpose |
|---------|---------|
| [`slog`](https://github.com/sivakov512/slog) | Structured tag-based logging (`SLOGI`, `SLOGE`, …) |
| [`embedlibs`](https://github.com/sivakov512/embedlibs) | Embedded utilities (`EXTERN_C_BEGIN/END`, etc.) |

---

## Makefile Reference

### ESP (on-device)

| Target | Description |
|--------|-------------|
| `esp-build` | Build the project (`idf.py build`) |
| `esp-flash` | Flash to device |
| `esp-flashm` | Flash and open serial monitor |
| `esp-monitor` | Open serial monitor only |
| `esp-lint` | Run clang-tidy on ESP sources |
| `esp-sanitize-db` | Patch `build/compile_commands.json` → `build/tidy/compile_commands.json` (called by `esp-lint`) |
| `esp-menuconfig` | Open IDF menuconfig |
| `esp-clean` | Full clean (build artifacts, managed components, cache) |

Override the default serial port: `make esp-flash PORT_ESP=/dev/ttyUSB0`

### Host tests

| Target | Description |
|--------|-------------|
| `host-build` | Build host test suite (CMake + Unity) |
| `host-test` | Run tests on the host machine |
| `host-lint` | Run clang-tidy on host-compatible components |
| `host-fullcheck` | `host-test` + `host-lint` |
| `host-clean` | Remove host build artifacts |

### Code quality

| Target | Description |
|--------|-------------|
| `check-format` | Verify formatting with clang-format (dry-run) |
| `lint` | `esp-lint` + `host-lint` + `check-format` |
| `fullcheck` | `lint` + `host-test` |
| `clean` | Clean all (ESP + host) |

### IDE helpers

| Target | Description |
|--------|-------------|
| `use-esp` | Symlink `compile_commands.json` → ESP build DB |
| `use-host` | Symlink `compile_commands.json` → host test build DB |

---

## clangd / IDE Integration

The `.clangd` config strips ESP-IDF's GCC-specific flags (`-mlongcalls`, `-mcpu=*`, `-march=*`, etc.) so that clangd works correctly in VS Code, CLion, Neovim, and any other LSP-capable editor.

Switch `compile_commands.json` between build targets:

```bash
make use-esp    # point clangd at the ESP build DB
make use-host   # point clangd at the host test build DB
```

---

## Host-Side Testing

The `tests/host/` directory uses [Unity](https://github.com/ThrowTheSwitch/Unity) fetched automatically via CMake `FetchContent`. Tests run natively — no hardware required.

```bash
make host-test
```

To add a component to the host test suite:

1. Add the component name to `LIBS2TEST` in `tests/host/CMakeLists.txt`.
2. Create a `tests/` directory inside the component.
3. Add a `CMakeLists.txt` using the `add_unity_test()` helper:

```cmake
add_unity_test(my_component_tests
    SRCS test_my_component.c
    LIBS my_component
)
```

Enable the `host-checks.yml` workflow once you have tests to run.

---

## Enabling ESP-Matter

1. Set the environment variable:
   ```bash
   export ESP_MATTER_PATH=/path/to/esp-matter
   ```

2. Enable in `CMakeLists.txt`:
   ```cmake
   set(ESP_MATTER_ENABLED true)
   ```

3. Clean and rebuild:
   ```bash
   make esp-clean
   make esp-build
   ```

**C++ standard:** ESP-IDF defaults to GNU C++23 (`-std=gnu++2b`). When Matter is enabled, Matter/CHIP components are compiled with `-std=gnu++17 -w` to avoid C++23 incompatibilities in upstream connectedhomeip; your code stays on C++23.

**CI:** The `esp-lint` workflow auto-detects `ESP_MATTER_ENABLED` and selects the correct Docker image — `ghcr.io/sivakov512/esp-idf` for plain builds or `ghcr.io/sivakov512/esp-matter` when Matter is active.

---

## Code Style

### clang-format

Based on **LLVM style** with project tweaks:

- 4-space indentation, 85-column limit
- Tabs → spaces
- Braces: `Attach`
- Sorted includes, blocks preserved

### clang-tidy

Checks enabled: `clang-diagnostic-*`, `clang-analyzer-*`, `bugprone-*`, `performance-*`, `portability-*`, `modernize-*`, `readability-*`, `misc-*`, plus select `google-*` rules. **All warnings are treated as errors.**

**Naming conventions:**

| Context | Convention | Example |
|---------|-----------|---------|
| C functions | `snake_case` | `app_init` |
| C structs / typedefs | `snake_case_t` | `app_ctx_t` |
| C++ classes / enums | `CamelCase` | `WifiManager` |
| C++ methods | `snake_case` | `connect` |
| C++ members | `snake_case_` | `retry_count_` |
| Class constants | `kCamelCase` | `kMaxRetries` |
| Enum values | `UPPER_CASE` | `STATE_IDLE` |
| Macros & global constants | `UPPER_CASE` | `TAG` |
| Global variables | `g_` prefix | `g_event_loop` |
| Namespaces | `lower_case` | `wifi` |

See [`.clang-tidy`](.clang-tidy) for the complete configuration.
