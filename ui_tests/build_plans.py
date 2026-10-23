# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

"""Writes the screenshot-test plans for one site.

Each plan is a list of steps for runner.mjs: open a URL in a theme mode and
viewport, run an optional setup script, then a probe that returns
{values, failed, checks}. Pages differ per site, so they are arguments.

	python -I build_plans.py <out-dir> --workspace /app/orith --doctype tenant
"""

import argparse
import json
from pathlib import Path

from desk_theme.theme.stylesheet import Brand, Palette, Scheme, ThemeConfig, build_css

HERE = Path(__file__).parent
PHONE = {"width": 390, "height": 844, "mobile": True, "deviceScaleFactor": 1}
SHEET_WAIT_MS = 900

# Theme mode as Frappe stores it, and the OS preference automatic follows.
MODES = {
	"light": ("light", "light"),
	"dark": ("dark", "light"),
	"auto_osdark": ("automatic", "dark"),
	"auto_oslight": ("automatic", "light"),
}

# Custom region colours: light-text and dark-text cases in both schemes.
CUSTOM = ThemeConfig(
	palette=Palette.SLATE,
	brands={
		Scheme.LIGHT: Brand(accent="#4F5D95", sidebar="#00998c", dock="#1e293b", topbar="#f6e9e3"),
		Scheme.DARK: Brand(accent="#8C9AD6", sidebar="#2b1d3a", dock="#e2e8f0", topbar="#334155"),
	},
)
BLANK = ThemeConfig(palette=Palette.SLATE, brands={Scheme.LIGHT: Brand(), Scheme.DARK: Brand()})

# Replace the live settings stylesheet with a fixed config, so results don't depend on saved settings.
DROP_LIVE = "document.querySelectorAll('link[href*=\"stylesheet_css\"]').forEach((l) => l.remove());"
OPEN_SHEET = "frappe.ui.mobile_nav.open_navigation();"
SHEET_CHECK = '\t} else {\n\t\tcheck("navigation sheet opened", false);\n\t}'

DIALOG = (
	"(() => { new frappe.ui.Dialog({ title: 'Theme check', fields: ["
	"{ fieldtype: 'Data', fieldname: 'name', label: 'Name' },"
	"{ fieldtype: 'Check', fieldname: 'ok', label: 'Checked', default: 1 }],"
	" primary_action_label: 'Save', primary_action() {} }).show(); return true; })()"
)
# New Contact: its Email IDs table edits inline; a filled row avoids the error ring.
GRID = (
	"(async () => { const row = cur_frm.add_child('email_ids'); row.email_id = 'theme.check@example.com';"
	" cur_frm.refresh_field('email_ids'); await new Promise((r) => setTimeout(r, 300));"
	" cur_frm.fields_dict.email_ids.grid.grid_rows[0].activate();"
	" await new Promise((r) => setTimeout(r, 800)); return true; })()"
)
FLOAT_DOCK = "(() => { document.body.classList.remove('dock-pinned'); document.body.classList.add('dock-open'); return true; })()"


def main():
	args = _parse()
	out = Path(args.out)
	out.mkdir(parents=True, exist_ok=True)

	probes = {p.stem: p.read_text().strip() for p in (HERE / "probes").glob("*.js")}
	desk_probe = _merge(probes["checks"], probes["selectors"])
	css = {"custom": build_css(CUSTOM), "blank": build_css(BLANK)}

	list_url = f"/app/{args.doctype}"
	pages = [
		("home", args.workspace, None),
		("list", list_url, None),
		("form_tables", "/app/navbar-settings", None),
		("grid_edit", "/app/contact/new", GRID),
		("dialog", list_url, DIALOG),
		("report", f"{list_url}/view/report", None),
		("settings", "/app/desk-theme-settings", None),
		("dock_float", list_url, FLOAT_DOCK),
	]

	plans = {
		"desk": _desk(pages, desk_probe),
		"regions": _regions(args.workspace, list_url, probes["regions"], css["custom"]),
		"mobile": _mobile(list_url, probes["mobile"], css, OPEN_SHEET),
		"bars": _mobile(list_url, probes["mobile"].replace(SHEET_CHECK, "\t}"), css, ""),
		"compat": _compat(probes["checks"]),
		"web": [{"name": "login__guest", "url": "/login", "probe": probes["checks"]}],
	}

	for name, plan in plans.items():
		(out / f"plan_{name}.json").write_text(json.dumps(plan))
		print(f"plan_{name}.json: {len(plan)} steps")


def _parse():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("out", help="directory for plan_*.json")
	parser.add_argument("--workspace", required=True, help="a workspace route, e.g. /app/orith")
	parser.add_argument("--doctype", required=True, help="a list-view route name, e.g. tenant")
	return parser.parse_args()


def _merge(*probes: str) -> str:
	"""One probe that runs several and sums their results."""
	calls = ", ".join(probes)
	return (
		f"(async () => {{ const rs = [{calls}]; return {{"
		" values: Object.assign({}, ...rs.map((r) => r.values)),"
		" failed: rs.flatMap((r) => r.failed), checks: rs.reduce((n, r) => n + r.checks, 0) }; })()"
	)


def _step(name, url, probe, mode=None, os_scheme="light", setup=None, viewport=None) -> dict:
	step = {"name": name, "url": url, "probe": probe, "os": os_scheme}
	if mode:
		step["mode"] = mode
	if setup:
		step["setup"] = setup
	if viewport:
		step["viewport"] = viewport
	return step


def _inject(css: str, then: str = "") -> str:
	style = f"const s = document.createElement('style'); s.textContent = {json.dumps(css)}; document.head.appendChild(s);"
	wait = f"await new Promise((r) => setTimeout(r, {SHEET_WAIT_MS}));"
	return f"(async () => {{ {DROP_LIVE} {style} {then} {wait} return true; }})()"


def _desk(pages, probe) -> list[dict]:
	steps = []
	for tag, (mode, os_scheme) in MODES.items():
		for name, url, setup in pages:
			steps.append(_step(f"{name}__{tag}", url, probe, mode, os_scheme, setup))
	return steps


def _regions(workspace, list_url, probe, css) -> list[dict]:
	return [
		_step(f"region_{name}_{mode}", url, probe, mode, setup=_inject(css))
		for mode in ("light", "dark")
		for name, url in (("list", list_url), ("home", workspace))
	]


def _mobile(list_url, probe, css, then) -> list[dict]:
	prefix = "mobile" if then else "bars"
	live = (
		f"(async () => {{ {then} await new Promise((r) => setTimeout(r, {SHEET_WAIT_MS})); return true; }})()"
	)
	steps = []
	for config in ("live", "custom", "blank"):
		setup = live if config == "live" else _inject(css[config], then)
		for mode in ("light", "dark"):
			steps.append(
				_step(f"{prefix}_{config}__{mode}", list_url, probe, mode, setup=setup, viewport=PHONE)
			)
	return steps


def _compat(probe) -> list[dict]:
	pages = [("user", "/app/user/Administrator"), ("system_settings", "/app/system-settings")]
	return [_step(f"compat_{n}__{m}", u, probe, m) for m in ("light", "dark") for n, u in pages]


if __name__ == "__main__":
	main()
