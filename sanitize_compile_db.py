#!/usr/bin/env python3
"""
Sanitize CMake's compile_commands.json for running clang-tidy on ESP-IDF projects.

- Drop GCC/ld-specific flags that confuse libclang.
- Replace compiler with clang/clang++ (analysis only) and add -fsyntax-only.
- Set parsing target: riscv32 for ESP32-C3/H2; fake host target + __XTENSA__ for Xtensa.
- Detect the real cross-GCC used by CMake (xtensa-…-gcc or riscv32-…-gcc),
  derive --gcc-toolchain=<root> and --sysroot=<sysroot>, and inject them
  into EVERY entry so clang-tidy needs no extra CLI flags.

Usage:
  idf.py reconfigure
  ./sanitize_compile_db.py build/compile_commands.json build/tidy/compile_commands.json
  clang-tidy -p build/tidy <files...>
"""

import json, os, shlex, sys, shutil, subprocess
from pathlib import Path

DROP_FLAGS_PREFIXES = [
    "-MMD",
    "-MP",
    "-MF",
    "-fstrict-volatile-bitfields",
    "-fno-builtin",
    "-Wl,",
    "-Wl",
    "-u",
    "-mlongcalls",
    "-mfix-esp32-psram-cache-issue",
    "-fno-tree-switch-conversion",
    "-fno-shrink-wrap",
]
DROP_FLAGS_EXACT = set()


def is_cpp(p):
    return os.path.splitext(p)[1] in [
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


def find_cross_from_db(db):
    """Find token like xtensa-…-(gcc|g++) or riscv32-…-(gcc|g++) from the JSON DB."""
    # Prefer first entry, but scan all if needed
    entries = db if isinstance(db, list) else []
    for e in [entries[0]] if entries else []:
        for tok in _tokens(e):
            if (tok.endswith(("gcc", "g++"))) and ("xtensa" in tok or "riscv" in tok):
                return tok
    for e in entries:
        for tok in _tokens(e):
            if (tok.endswith(("gcc", "g++"))) and ("xtensa" in tok or "riscv" in tok):
                return tok
    return None


def _tokens(entry):
    cmd = entry.get("command") or entry.get("arguments")
    if isinstance(cmd, str):
        return shlex.split(cmd)
    return list(cmd or [])


def resolve_toolchain_and_sysroot(cross_name):
    """Return (toolchain_root_path_str, sysroot_path_str)."""
    p = Path(cross_name)
    if not p.exists():
        which = shutil.which(cross_name)
        if not which:
            raise RuntimeError(
                f"Cross-compiler not found on PATH: {cross_name}. Did you source IDF export.sh?"
            )
        p = Path(which)
    toolchain_root = p.parent.parent  # .../bin -> root
    try:
        sysroot = subprocess.check_output([str(p), "-print-sysroot"], text=True).strip()
    except subprocess.CalledProcessError as ex:
        raise RuntimeError(f"Failed to get sysroot via '{p} -print-sysroot'") from ex
    if not sysroot:
        raise RuntimeError("Empty sysroot detected")
    return str(toolchain_root), sysroot


def sanitize_entry(e, extra_args):
    src = e.get("file")
    argv = _tokens(e)

    fam = guess_family(argv)
    # use clang front-end
    compiler = "clang++" if is_cpp(src) else "clang"
    cleaned = [compiler]

    i = 1
    while i < len(argv):
        a = argv[i]
        if a in DROP_FLAGS_EXACT:
            i += 1
            continue
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

    # inject toolchain hints
    cleaned += extra_args

    out = dict(e)
    out["arguments"] = cleaned
    out.pop("command", None)
    return out


def main(src, dst):
    db = json.loads(Path(src).read_text())
    cross = find_cross_from_db(db)
    if not cross:
        raise SystemExit(
            "ERROR: cannot detect cross-compiler (xtensa/riscv gcc) from compile_commands.json"
        )

    toolchain_root, sysroot = resolve_toolchain_and_sysroot(cross)
    extra = [
        f"--gcc-toolchain={toolchain_root}",
        f"--sysroot={sysroot}",
    ]

    out = []
    for ent in db:
        try:
            out.append(sanitize_entry(ent, extra))
        except Exception as ex:
            print(f"[sanitize] skip {ent.get('file')}: {ex}", file=sys.stderr)
    Path(dst).write_text(json.dumps(out, indent=2))
    print(f"Sanitized -> {dst} ({len(out)} entries)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: sanitize_compile_db.py <input> <output>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
