#!/usr/bin/env bash
# Stack-agnostic HTTP smoke test used by refactor-arch (Phase 3).
#
# Usage: smoke.sh BASE_URL REQUESTS_FILE OUT_FILE [HEADER ...]
#   REQUESTS_FILE: one request per line -> "METHOD PATH [JSON_BODY]"; blank lines and '#' comments ignored.
#   OUT_FILE:      receives "STATUS METHOD PATH" per request (diff-friendly).
#   OUT_FILE.bodies receives each request followed by its response body.
#   HEADER:        extra headers sent with every request, e.g. "X-Admin-Token: abc".
# Exit code: 0 if every request got an HTTP response below 500; 1 otherwise.
set -u

if [ "$#" -lt 3 ]; then
  echo "usage: $0 BASE_URL REQUESTS_FILE OUT_FILE [HEADER ...]" >&2
  exit 2
fi

base_url="${1%/}"; requests_file="$2"; out_file="$3"; shift 3
extra_headers=()
for header in "$@"; do extra_headers+=(-H "$header"); done

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT
: > "$out_file"
: > "$out_file.bodies"
failures=0

while IFS= read -r line || [ -n "$line" ]; do
  line="${line%$'\r'}"
  case "$line" in ''|'#'*) continue ;; esac

  method="${line%% *}"
  rest="${line#* }"
  path="${rest%% *}"
  payload=""
  [ "$path" != "$rest" ] && payload="${rest#* }"

  args=(-s -o "$body_file" -w '%{http_code}' --max-time 15 -X "$method")
  args+=(${extra_headers[@]+"${extra_headers[@]}"})
  if [ -n "$payload" ]; then
    args+=(-H 'Content-Type: application/json' --data-raw "$payload")
  fi

  status="$(curl "${args[@]}" "$base_url$path")"
  [ -z "$status" ] && status="000"

  printf '%s %s %s\n' "$status" "$method" "$path" >> "$out_file"
  {
    printf '### %s %s %s\n-> %s\n' "$method" "$path" "$payload" "$status"
    cat "$body_file"
    printf '\n\n'
  } >> "$out_file.bodies"

  if [ "$status" = "000" ] || [ "$status" -ge 500 ]; then
    failures=$((failures + 1))
  fi
done < "$requests_file"

total="$(wc -l < "$out_file" | tr -d ' ')"
echo "smoke: $total requests, $failures failures (000/5xx) -> $out_file"
[ "$failures" -eq 0 ]
