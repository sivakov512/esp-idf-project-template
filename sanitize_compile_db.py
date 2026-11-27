#!/usr/bin/env python3
"""
Prepare a compile_commands.json for clang-tidy and clangd from Espressif LLVM
(esp-clang / esp-clangd).

ESP mode (default), for build/compile_commands.json written by ESP-IDF:
- Expand GCC response files (ESP-IDF v6 keeps toolchain flags such as
  -mlongcalls and -specs=picolibc.specs in build/toolchain/cflags).
- Drop GCC/ld-specific flags that clang does not know.
- Use the real target: xtensa-esp-elf with -mcpu=<chip>, or riscv32-esp-elf.
- Ask the real cross-GCC (xtensa-…-gcc or riscv32-…-gcc) for its system
  include directories, with the same -specs/-m flags the build uses, and pass
  exactly those via -nostdlibinc + -isystem. This picks the right C library
  headers whether the project uses picolibc (ESP-IDF v6 default) or newlib
  (CONFIG_LIBC_NEWLIB), plus the libstdc++ headers for the selected multilib.

Host mode (--host), for the host tests' compile_commands.json:
- Pass the host target explicitly (esp-clang defaults to riscv32-esp-elf)
  and, on macOS, the SDK as -isysroot.

Both modes add -resource-dir of esp-clang: esp-clangd ships without clang's
builtin headers (stddef.h, stdarg.h, ...).

Usage:
  idf.py reconfigure
  ./sanitize_compile_db.py build/compile_commands.json build/tidy/compile_commands.json
  clang-tidy -p build/tidy <files...>

  ./sanitize_compile_db.py --host tests/host/build/compile_commands.json \\
      tests/host/build/tidy/compile_commands.json
"""

import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DROP_FLAGS_PREFIXES = [
    "-MMD",
    "-MP",
    "-fstrict-volatile-bitfields",
    "-fno-builtin",
    "-Wl",
    "-u",
    "-mlongcalls",
    "-mfix-esp32-psram-cache-issue",
    "-fno-tree-switch-conversion",
    "-fno-shrink-wrap",
    "-mdisable-hardware-atomics",
    "-mtune=",
    "-specs=",
    "--specs=",
    "-fno-malloc-dce",
    "-fzero-init-padding-bits",
]

# Flags that change which system headers GCC uses (spec files, multilib).
INCLUDE_AFFECTING_PREFIXES = ("-specs=", "--specs=", "-m", "--sysroot", "-isysroot")

ESP_CLANG_HINT = (
    "Espressif LLVM (esp-clang) is required. Install it with\n"
    "  python $IDF_PATH/tools/idf_tools.py install esp-clang\n"
    "and source the ESP-IDF export script again."
)


def is_cpp(p):
    return Path(p).suffix in [
        ".cc",
        ".cpp",
        ".cxx",
        ".C",
        ".hpp",
        ".hh",
        ".hxx",
    ]


def is_cross_gcc(tok):
    return tok.endswith(("gcc", "g++")) and ("xtensa" in tok or "riscv" in tok)


def _tokens(entry):
    cmd = entry.get("command") or entry.get("arguments")
    if isinstance(cmd, str):
        return shlex.split(cmd)
    return list(cmd or [])


def find_esp_clang():
    """Return (bin_dir, resource_dir) of esp-clang found on PATH."""
    clang = shutil.which("clang")
    if not clang:
        raise SystemExit(f"ERROR: clang not found on PATH.\n{ESP_CLANG_HINT}")
    version = subprocess.run([clang, "--version"], capture_output=True, text=True).stdout
    if "Espressif" not in version:
        raise SystemExit(f"ERROR: {clang} is not Espressif LLVM.\n{ESP_CLANG_HINT}")
    resource_dir = subprocess.check_output([clang, "-print-resource-dir"], text=True).strip()
    return Path(clang).resolve().parent, resource_dir


def expand_response_files(argv, cwd, depth=0):
    """Inline @file arguments the way GCC does, relative to the entry's directory."""
    out = []
    for a in argv:
        if a.startswith("@") and depth < 10:
            p = Path(a[1:])
            if not p.is_absolute():
                p = Path(cwd) / p
            if p.is_file():
                out += expand_response_files(shlex.split(p.read_text()), cwd, depth + 1)
                continue
        out.append(a)
    return out


def drop_gcc_flags(argv):
    cleaned = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if any(a.startswith(p) for p in DROP_FLAGS_PREFIXES):
            i += 1
            continue
        if a in ("-MF", "-MT", "-MQ"):
            i += 2
            continue
        if a in ("-nostdinc", "-nostdlib", "-nodefaultlibs"):
            i += 1
            continue
        cleaned.append(a)
        i += 1
    return cleaned


_cache = {}


def run_cached(cmd, cwd):
    key = (tuple(cmd), cwd)
    if key not in _cache:
        try:
            _cache[key] = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, check=True
            )
        except FileNotFoundError as ex:
            raise SystemExit(f"ERROR: compiler not found: {cmd[0]}") from ex
        except subprocess.CalledProcessError as ex:
            raise SystemExit(f"ERROR: '{shlex.join(cmd)}' failed:\n{ex.stderr}") from ex
    return _cache[key]


def gcc_system_includes(compiler, lang, flags, cwd):
    """Return GCC's <...> include search list for these flags, minus GCC's own
    builtin headers (clang uses its resource dir for stddef.h, stdarg.h, ...)."""
    cmd = [compiler, *flags, "-x", lang, "-E", "-Wp,-v", "-o", "/dev/null", "/dev/null"]
    res = run_cached(cmd, cwd)

    dirs = []
    in_list = False
    for line in res.stderr.splitlines():
        if line.startswith("#include <...> search starts here:"):
            in_list = True
            continue
        if line.startswith("End of search list."):
            break
        if in_list and line.startswith(" "):
            d = Path(line.strip()).resolve()
            # lib/gcc/<triple>/<version>/include{,-fixed}: GCC's freestanding headers
            if "lib/gcc" in d.as_posix() and d.name in ("include", "include-fixed"):
                continue
            dirs.append(str(d))

    if not dirs:
        raise SystemExit(f"ERROR: no system include dirs reported by '{shlex.join(cmd)}'")
    return dirs


def esp_target_args(compiler):
    name = Path(compiler).name
    if name.startswith("riscv32-"):
        return ["--target=riscv32-esp-elf"]
    # xtensa-esp32s3-elf-gcc -> esp32s3
    return ["--target=xtensa-esp-elf", f"-mcpu={name.split('-')[1]}"]


def sanitize_esp_entry(e, bin_dir, resource_dir):
    src = e.get("file")
    cwd = e.get("directory", ".")
    argv = _tokens(e)
    if not argv or not is_cross_gcc(argv[0]):
        raise ValueError("not built with the ESP cross-compiler")
    argv = [argv[0]] + expand_response_files(argv[1:], cwd)
    cpp = is_cpp(src)

    # GCC-only warning options (e.g. -Wno-error=maybe-uninitialized, added by
    # some components) are ignored instead of failing as unknown options.
    cleaned = [str(bin_dir / ("clang++" if cpp else "clang")), "-Wno-unknown-warning-option"]
    cleaned += drop_gcc_flags(argv[1:])
    cleaned += esp_target_args(argv[0])
    cleaned += ["-fsyntax-only", f"-resource-dir={resource_dir}"]

    # system headers exactly as the cross-GCC sees them
    query_flags = [a for a in argv[1:] if a.startswith(INCLUDE_AFFECTING_PREFIXES)]
    includes = gcc_system_includes(argv[0], "c++" if cpp else "c", query_flags, cwd)
    # The system headers come from GCC below, so esp-clang's own multilib
    # selection is not used; without this it warns for some RISC-V -march sets.
    cleaned += ["-nostdlibinc", "-Wno-extern-c-compat", "-Wno-missing-multilib"]
    for d in includes:
        cleaned += ["-isystem", d]
    return cleaned


def macos_sdk():
    if platform.system() != "Darwin":
        return None
    try:
        return subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def sanitize_host_entry(e, bin_dir, resource_dir, sdk):
    src = e.get("file")
    cwd = e.get("directory", ".")
    argv = _tokens(e)
    if not argv:
        raise ValueError("empty command")
    argv = [argv[0]] + expand_response_files(argv[1:], cwd)
    triple = run_cached([argv[0], "-dumpmachine"], cwd).stdout.strip()

    cleaned = [str(bin_dir / ("clang++" if is_cpp(src) else "clang")), "-Wno-unknown-warning-option"]
    cleaned += drop_gcc_flags(argv[1:])
    cleaned += [f"--target={triple}", "-fsyntax-only", f"-resource-dir={resource_dir}"]
    if sdk and "-isysroot" not in cleaned:
        cleaned += ["-isysroot", sdk]
    return cleaned


def main(args):
    host = "--host" in args
    paths = [a for a in args if a != "--host"]
    if len(paths) != 2:
        print("usage: sanitize_compile_db.py [--host] <input> <output>")
        sys.exit(2)
    src, dst = paths

    db = json.loads(Path(src).read_text())
    bin_dir, resource_dir = find_esp_clang()
    if not host and not any(is_cross_gcc(t) for e in db for t in _tokens(e)[:1]):
        raise SystemExit(
            "ERROR: cannot detect cross-compiler (xtensa/riscv gcc) from compile_commands.json"
        )
    sdk = macos_sdk() if host else None

    out = []
    for ent in db:
        try:
            if host:
                cleaned = sanitize_host_entry(ent, bin_dir, resource_dir, sdk)
            else:
                cleaned = sanitize_esp_entry(ent, bin_dir, resource_dir)
        except ValueError as ex:
            print(f"[sanitize] skip {ent.get('file')}: {ex}", file=sys.stderr)
            continue
        item = dict(ent)
        item["arguments"] = cleaned
        item.pop("command", None)
        out.append(item)

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(json.dumps(out, indent=2))
    print(f"Sanitized -> {dst} ({len(out)} entries)")


if __name__ == "__main__":
    main(sys.argv[1:])
