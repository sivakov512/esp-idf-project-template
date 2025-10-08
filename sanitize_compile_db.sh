#!/usr/bin/env sh
set -eu

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq not found (install: apt-get install jq / brew install jq)" >&2
  exit 1
fi

if [ $# -lt 2 ] || [ $# -gt 3 ]; then
  echo "usage: $0 <input compile_commands.json> <output json> [host-triple]" >&2
  exit 2
fi

IN="$1"
OUT="$2"

if [ $# -eq 3 ]; then
  HOST_TRIPLE="$3"
else
  case "$(uname -s)" in
    Darwin) HOST_TRIPLE="$(uname -m)-apple-darwin" ;;
    *)      HOST_TRIPLE="x86_64-unknown-linux-gnu" ;;
  esac
fi

JQ_FILTER='
  def dropflags:
    map(
      select(. != "-mlongcalls")
      | select(. != "-fno-shrink-wrap")
      | select(. != "-fno-tree-switch-conversion")
      | select(. != "-fstrict-volatile-bitfields")
    );

  map(
    if has("arguments") then
      .arguments = (
        (.arguments // [])                      # массив аргументов
        | dropflags
        + ["-target", $t, "-Wno-unused-command-line-argument"]
      )
    elif has("command") then
      .command = (
        .command
        | gsub(" -mlongcalls";"")
        | gsub(" -fno-shrink-wrap";"")
        | gsub(" -fno-tree-switch-conversion";"")
        | gsub(" -fstrict-volatile-bitfields";"")
        | gsub(" -target xtensa-[^ ]+";" -target " + $t)
        + " -Wno-unused-command-line-argument"
      )
    else
      .
    end
  )
'

mkdir -p "$(dirname "$OUT")"
jq --arg t "$HOST_TRIPLE" "$JQ_FILTER" "$IN" > "$OUT"
echo "Sanitized compile DB -> $OUT (target=$HOST_TRIPLE)"
