#!/usr/bin/env bash
# Screenshot UI tests for desk_theme against one running site.
#
#   ui_tests/run.sh <bench-dir> <site> <origin> <workspace-route> <doctype> [out-dir]
#   ui_tests/run.sh ~/frappe/sites/orith.localhost orith.localhost http://orith.localhost:8003 /app/orith tenant
#
# Needs: the site served at <origin> with redis up, developer_mode (for the
# Administrator session), google-chrome, node >= 22. Writes screenshots,
# results and contact sheets to <out-dir>; prints failed checks and a total.
set -euo pipefail

BENCH=$1
SITE=$2
ORIGIN=$3
WORKSPACE=$4
DOCTYPE=$5
OUT=${6:-$(mktemp -d)}
HERE=$(cd "$(dirname "$0")" && pwd)
SESSION_MINUTES=60
DESK_PLANS="desk regions mobile bars compat"

# Short-lived Administrator session for the headless browser; never printed.
SESSION_END=$(date -u -d "+${SESSION_MINUTES} minutes" +%Y-%m-%dT%H:%M:%S+00:00)
SID=$(cd "$BENCH" && bench --site "$SITE" browse --user Administrator --sid --session-end "$SESSION_END" 2>/dev/null | tail -1)

"$BENCH/env/bin/python" -I "$HERE/build_plans.py" "$OUT" --workspace "$WORKSPACE" --doctype "$DOCTYPE"

for plan in $DESK_PLANS; do
	ORIGIN=$ORIGIN SID=$SID node "$HERE/runner.mjs" "$OUT/plan_$plan.json" "$OUT" > "$OUT/result_$plan.json"
done
ORIGIN=$ORIGIN node "$HERE/runner.mjs" "$OUT/plan_web.json" "$OUT" > "$OUT/result_web.json"

# Sheets before the summary: it exits 1 on failures, which set -e would
# turn into "no sheets" exactly when they are needed. Its status is ours.
"$BENCH/env/bin/python" -I "$HERE/sheet.py" "$OUT" "$OUT/sheet" > /dev/null
echo "Screenshots and contact sheets: $OUT"
python3 "$HERE/summarize.py" "$OUT"
