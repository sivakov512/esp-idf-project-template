#!/usr/bin/env python3
"""
Sanitize CMake's compile_commands.json for running clang-tidy on ESP-IDF projects.

- Expand GCC response files (ESP-IDF v6 keeps toolchain flags such as
  -mlongcalls and -specs=picolibc.specs in build/toolchain/cflags).
- Drop GCC/ld-specific flags that confuse libclang.
- Replace compiler with clang/clang++ (analysis only) and add -fsyntax-only.
- Set parsing target: riscv32 for ESP32-C3/H2; fake host target + __XTENSA__ for Xtensa.
- Ask the real cross-GCC used by CMake (xtensa-…-gcc or riscv32-…-gcc) for its
  system include directories, with the same -specs/-m flags the build uses,
  and pass exactly those to clang via -nostdlibinc + -isystem. This picks the
  right C library headers whether the project uses picolibc (ESP-IDF v6
  default) or newlib (ESP-IDF v5.x), plus the libstdc++ headers for the
  selected multilib, so clang-tidy needs no extra CLI flags.

Usage:
  idf.py reconfigure
  ./sanitize_compile_db.py build/compile_commands.json build/tidy/compile_commands.json
  clang-tidy -p build/tidy <files...>
"""

import json
import shlex
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
    "-Wno-old-style-declaration",
]

# Flags that change which system headers GCC uses (spec files, multilib).
INCLUDE_AFFECTING_PREFIXES = ("-specs=", "--specs=", "-m", "--sysroot", "-isysroot")


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


def guess_family(argv):
    s = " ".join(argv)
    if "riscv32-" in s:
        return "riscv"
    if "xtensa-" in s:
        return "xtensa"
    return "host"


def is_cross_gcc(tok):
    return tok.endswith(("gcc", "g++")) and ("xtensa" in tok or "riscv" in tok)


def _tokens(entry):
    cmd = entry.get("command") or entry.get("arguments")
    if isinstance(cmd, str):
        return shlex.split(cmd)
    return list(cmd or [])


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


_include_cache = {}


def gcc_system_includes(compiler, lang, flags, cwd):
    """Return GCC's <...> include search list for these flags, minus GCC's own
    builtin headers (clang uses its resource dir for stddef.h, stdarg.h, ...)."""
    key = (compiler, lang, tuple(flags), cwd)
    if key in _include_cache:
        return _include_cache[key]

    cmd = [compiler, *flags, "-x", lang, "-E", "-Wp,-v", "-o", "/dev/null", "/dev/null"]
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    except FileNotFoundError as ex:
        raise SystemExit(
            f"ERROR: cross-compiler not found: {compiler}. Did you source IDF export.sh?"
        ) from ex
    except subprocess.CalledProcessError as ex:
        raise SystemExit(
            f"ERROR: '{shlex.join(cmd)}' failed:\n{ex.stderr}"
        ) from ex

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

    _include_cache[key] = dirs
    return dirs


def sanitize_entry(e):
    src = e.get("file")
    cwd = e.get("directory", ".")
    argv = _tokens(e)
    if not argv or not is_cross_gcc(argv[0]):
        raise ValueError("not built with the ESP cross-compiler")
    argv = [argv[0]] + expand_response_files(argv[1:], cwd)

    fam = guess_family(argv)
    cpp = is_cpp(src)
    # use clang front-end
    compiler = "clang++" if cpp else "clang"
    cleaned = [compiler]

    i = 1
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

    # Targets for parsing
    if fam == "riscv":
        if "-target" not in cleaned:
            cleaned += ["-target", "riscv32"]
    elif fam == "xtensa":
        if "-target" not in cleaned:
            cleaned += ["-target", "x86_64-unknown-linux-gnu"]
        cleaned += ["-D__XTENSA__"]

    # analysis only
    if "-fsyntax-only" not in cleaned:
        cleaned.append("-fsyntax-only")

    # system headers exactly as the cross-GCC sees them
    query_flags = [a for a in argv[1:] if a.startswith(INCLUDE_AFFECTING_PREFIXES)]
    includes = gcc_system_includes(argv[0], "c++" if cpp else "c", query_flags, cwd)
    cleaned += ["-nostdlibinc", "-Wno-extern-c-compat"]
    for d in includes:
        cleaned += ["-isystem", d]

    out = dict(e)
    out["arguments"] = cleaned
    out.pop("command", None)
    return out


def main(src, dst):
    db = json.loads(Path(src).read_text())
    if not any(is_cross_gcc(t) for e in db for t in _tokens(e)[:1]):
        raise SystemExit(
            "ERROR: cannot detect cross-compiler (xtensa/riscv gcc) from compile_commands.json"
        )

    out = []
    for ent in db:
        try:
            out.append(sanitize_entry(ent))
        except ValueError as ex:
            print(f"[sanitize] skip {ent.get('file')}: {ex}", file=sys.stderr)
    Path(dst).write_text(json.dumps(out, indent=2))
    print(f"Sanitized -> {dst} ({len(out)} entries)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: sanitize_compile_db.py <input> <output>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
