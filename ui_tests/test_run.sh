#!/usr/bin/env bash
# Checks run.sh still writes contact sheets when a check fails, and still
# exits non-zero. Stubs `bench` and `node` on PATH, so no site or browser.
#
#   ui_tests/test_run.sh <bench-dir>
set -uo pipefail

BENCH=$1
HERE=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Stubs: bench prints a fake session; node reports one failed check.
mkdir -p "$TMP/bin" "$TMP/out"
printf '#!/bin/sh\necho fake-sid\n' > "$TMP/bin/bench"
printf '#!/bin/sh\necho %s\n' "'{\"fake__light\": {\"checks\": 1, \"failed\": [\"forced\"], \"values\": {}}}'" > "$TMP/bin/node"
chmod +x "$TMP/bin/bench" "$TMP/bin/node"

# One screenshot for sheet.py to tile.
"$BENCH/env/bin/python" -I -c "from PIL import Image; Image.new('RGB', (8, 8)).save('$TMP/out/fake__light.png')"

PATH="$TMP/bin:$PATH" "$HERE/run.sh" "$BENCH" site http://site /app/x note "$TMP/out" > "$TMP/log" 2>&1
STATUS=$?

FAILED=0
if [ "$STATUS" -eq 0 ]; then
	echo "FAIL: run.sh exited 0 with a failed check"
	FAILED=1
fi

if [ ! -f "$TMP/out/sheet_1.png" ]; then
	echo "FAIL: no contact sheet written"
	FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
	cat "$TMP/log"
	exit 1
fi

echo "OK"
