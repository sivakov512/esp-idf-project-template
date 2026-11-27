# ESP-IDF Project Template

An ESP-IDF project base with clang-tidy, clangd, and CI pre-configured, host-side unit tests ready to run, and optional ESP-Matter support. Start writing firmware, not tooling config.

[![ESP Lint](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/esp-lint.yml/badge.svg)](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/esp-lint.yml)
[![Formatting](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/formatting.yml/badge.svg)](https://github.com/sivakov512/esp-idf-project-template/actions/workflows/formatting.yml)

## What's included

- **clang-format, clang-tidy, and clangd work out of the box, the same everywhere** — the editor, `make` and CI all use Espressif LLVM 21 (esp-clang / esp-clangd from ESP-IDF). [`sanitize_compile_db.py`](sanitize_compile_db.py) turns ESP-IDF's `compile_commands.json` into one clang understands: real Xtensa / RISC-V target, GCC-only flags dropped, the same system headers the cross-GCC uses (picolibc or newlib)
- **CI pre-configured** — GitHub Actions for static analysis and formatting; auto-selects the correct Docker image when Matter is enabled
- **Host-side unit tests** — [Unity](https://github.com/ThrowTheSwitch/Unity) via CMake `FetchContent`; test business logic without hardware
- **App structure** — `main/` entry point + `components/app/` business logic, ready to expand
- **Optional ESP-Matter** — connectedhomeip integration with C++17 pinning for Matter components

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/) | v6.1+ | Required; CI uses v6.1.1 |
| CMake | 3.16+ | For host tests |
| esp-clang | as listed by ESP-IDF (21.1.3 for v6.1.1) | Required for lint and formatting: `python $IDF_PATH/tools/idf_tools.py install esp-clang`. esp-clangd comes with ESP-IDF |
| [ESP-Matter](https://docs.espressif.com/projects/esp-matter/en/latest/esp32/developing.html) | release/v1.6.1+ | Optional; on ESP-IDF v6.0.2, as esp-matter recommends |

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
├── .clangd                     # Makes clangd use the prepared database for every file
├── sanitize_compile_db.py      # Prepares compile_commands.json for esp-clang / esp-clangd
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
| `esp-sanitize-db` | Prepare `build/compile_commands.json` → `build/tidy/compile_commands.json` (called by `esp-lint` and `use-esp`) |
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
| `use-esp` | Prepare the ESP database and symlink `compile_commands.json` to it |
| `use-host` | Prepare the host test database and symlink `compile_commands.json` to it |
| `zed` | Write `.zed/settings.json` for this machine: Zed uses esp-clangd, format on save |

---

## Editor Integration (clangd)

All checks use one toolchain, Espressif LLVM from ESP-IDF: `make` and CI run esp-clang's `clang-tidy` and `clang-format`, the editor runs esp-clangd. Diagnostics, `.clang-tidy` checks and formatting are the same in all three. The only difference: clangd does not run the slow `clang-analyzer-*` checks, so those show up in `make esp-lint` and CI only.

Upstream clangd cannot parse code for Xtensa, so the editor must use esp-clangd. It comes with ESP-IDF and is on `PATH` after the export script.

`compile_commands.json` in the project root points at a prepared database (see [`sanitize_compile_db.py`](sanitize_compile_db.py)); `.clangd` makes clangd use it for every file. Switch it between the ESP firmware and the host tests:

```bash
make use-esp    # ESP build (default)
make use-host   # host tests
```

### Zed

```bash
make zed
```

writes `.zed/settings.json` for this project only: clangd is esp-clangd (by absolute path, as Zed requires, so the file is machine-specific and git-ignored), with `--clang-tidy`, and C/C++ are formatted on save through clangd. Your global Zed settings stay as they are. Run it again after upgrading ESP-IDF.

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

**C++ standard:** ESP-IDF v6 defaults to GNU C++26 (`-std=gnu++26`). When Matter is enabled, Matter/CHIP components are compiled with `-std=gnu++17 -w` to avoid incompatibilities with newer standards in upstream connectedhomeip; your code stays on the IDF default.

**CI:** The `esp-lint` workflow auto-detects `ESP_MATTER_ENABLED` and selects the correct Docker image — `ghcr.io/sivakov512/esp-idf` for plain builds or `ghcr.io/sivakov512/esp-matter` (ESP-Matter release/v1.6.1 on ESP-IDF v6.0.2) when Matter is active. Both images carry the same esp-clang.

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

Headers use include guards (`#ifndef APP_H` / `#define APP_H`), not `#pragma once`: clang-tidy rejects it with `portability-avoid-pragma-once`.

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
