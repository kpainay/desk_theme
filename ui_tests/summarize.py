# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

"""Prints failed checks per step and a total from runner.mjs results.

Also fails a themed step that did not render in its theme: a lost session
lands on /login (no data-theme), where most checks would pass vacuously.
"""

import json
import sys
from pathlib import Path

ERROR_PREVIEW_CHARS = 200
AUTOMATIC = "automatic"


def main():
	out = Path(sys.argv[1])
	total = failed = 0

	for path in sorted(out.glob("result_*.json")):
		expected = _expected_themes(out / path.name.replace("result_", "plan_"))

		for step, result in json.loads(path.read_text()).items():
			if not isinstance(result, dict) or "checks" not in result:
				print(f"ERROR {step}: {str(result)[:ERROR_PREVIEW_CHARS]}")
				failed += 1
				continue

			total += result["checks"] + 1
			problems = list(result["failed"])
			theme = result.get("values", {}).get("theme")
			if step in expected and theme != expected[step]:
				problems.append(f"rendered theme {theme!r}, expected {expected[step]!r} (logged out?)")

			failed += len(problems)
			if problems:
				print(f"FAIL {step}: {problems}")

	print(f"TOTAL {total} checks, {failed} failed")
	sys.exit(1 if failed else 0)


def _expected_themes(plan_path: Path) -> dict[str, str]:
	"""Step name -> data-theme it must render with. Automatic follows the OS."""
	if not plan_path.exists():
		return {}

	expected = {}
	for step in json.loads(plan_path.read_text()):
		mode = step.get("mode")
		if not mode:
			continue

		expected[step["name"]] = step.get("os", "light") if mode == AUTOMATIC else mode

	return expected


if __name__ == "__main__":
	main()
