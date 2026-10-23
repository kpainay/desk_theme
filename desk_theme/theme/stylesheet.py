# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

"""Dynamic half of the desk theme, built from `Desk Theme Settings`.

Emits two kinds of custom properties; the static theme.css maps them onto
Frappe's tokens:

    --gray-50…950   Frappe's neutral ramp, tinted by the chosen palette
    --desk-theme-*       brand colours: accent, accent text, sidebar, dock, top bar

    Desk Theme Settings ─► ThemeConfig ─► build_css() ─► /api/method/desk_theme.theme.api.stylesheet_css
                                       └─► find_problems() ─► settings validate()

A blank brand colour is emitted as `initial` (CSS "guaranteed-invalid"), so
`var(--desk-theme-x, <fallback>)` in theme.css uses Frappe's own value, and a
light-scheme colour never leaks into dark mode.
"""

from dataclasses import dataclass
from enum import StrEnum

import frappe
from frappe import _
from frappe.utils import escape_html

from desk_theme.theme import colors

SETTINGS_DOCTYPE = "Desk Theme Settings"
UNSET = "initial"
WHITE = "#ffffff"


class Palette(StrEnum):
	SLATE = "Slate"
	ZINC = "Zinc"
	NEUTRAL = "Neutral"


class Scheme(StrEnum):
	LIGHT = "Light"
	DARK = "Dark"


# (hue in degrees, HSL saturation) laid over Frappe's greys. Neutral keeps them.
# Slate matches Tailwind slate at mid-greys (~16%); more reads as link-blue.
PALETTE_TINTS = {
	Palette.SLATE: (215, 0.16),
	Palette.ZINC: (240, 0.06),
}

# Mirrors frappe/public/css/espresso/colors.css. test_stylesheet fails on drift.
FRAPPE_GRAYS = {
	Scheme.LIGHT: {
		"50": "#f8f8f8",
		"100": "#f3f3f3",
		"200": "#ededed",
		"300": "#e2e2e2",
		"400": "#c7c7c7",
		"500": "#999999",
		"600": "#7c7c7c",
		"700": "#525252",
		"800": "#383838",
		"900": "#171717",
		"950": "#0f0f0f",
	},
	Scheme.DARK: {
		"50": "#f8f8f8",
		"100": "#d9d9d9",
		"200": "#afafaf",
		"300": "#999999",
		"400": "#7a7a7a",
		"450": "#575757",
		"500": "#424242",
		"600": "#383838",
		"700": "#292929",
		"800": "#242424",
		"900": "#1f1f1f",
		"950": "#171717",
	},
}

# Frappe's selectors, with `html` added to the root ones: html:root (0,1,1)
# outranks Frappe's :root (0,1,0) even when a Frappe bundle loads after us
# (login.bundle.css re-declares every token). Dark gets the same weight, so
# it still beats the light block on <html>. Plain [data-theme] keeps
# theme-switcher previews themed.
SCHEME_SELECTORS = {
	Scheme.LIGHT: 'html:root,\n[data-theme="light"]',
	Scheme.DARK: 'html[data-theme="dark"],\n[data-theme="dark"],\n.dark',
}

# Shades Frappe paints with, for contrast checks:
#   page  = --surface-base (white in light, gray-950 in dark)
#   text  = --ink-gray-8   (gray-900 in light, gray-100 in dark)
PAGE_SHADE = {Scheme.LIGHT: None, Scheme.DARK: "950"}

# Settings field suffix per scheme. e.g. accent_color / accent_color_dark.
FIELD_SUFFIX = {Scheme.LIGHT: "", Scheme.DARK: "_dark"}


class Region(StrEnum):
	SIDEBAR = "Sidebar"
	DOCK = "Dock"
	TOPBAR = "Top Bar"


# A region with a custom colour gets its own ink, hover and border tokens,
# scoped to its markup, so text stays readable on any colour:
#
#   html (page scheme)        --ink-gray-8: page text   → saved as --desk-theme-root-ink-gray-8
#    └─ .body-sidebar         --ink-gray-8: derived from the sidebar colour
#        └─ .dropdown-menu    --ink-gray-8: var(--desk-theme-root-ink-gray-8)  (page again)
#
# On phones the dock's job moves to the tab bar and the navigation sheet's top
# row, and the sidebar's to the navigation sheet (mobile_nav.js).
#
# FRAPPE MARKUP: re-check these selectors after `bench update`.
REGION_SELECTORS = {
	Region.SIDEBAR: (".body-sidebar", ".es-bottom-sheet:has(.desk-mobile-sheet)"),
	Region.DOCK: (
		".dock",
		".desk-mobile-sheet-dock",
		'frappe-mobile-nav.desk-mobile-nav [data-slot="mobile-nav"]',
	),
	Region.TOPBAR: (".page-head", ".navbar-light"),
}
REGION_MENUS = '.dropdown-menu, .popover, [role="menu"]'
SCHEME_SCOPE = {
	Scheme.LIGHT: 'html:not([data-theme="dark"])',
	Scheme.DARK: 'html[data-theme="dark"]',
}
ROOT_COPY_PREFIX = "--desk-theme-root-"

# Hover/pressed surfaces and outlines in a region: share of the region's text
# colour mixed into the region colour. e.g. hover (--surface-gray-2) is 8% text.
REGION_SURFACES = {
	"--surface-gray-1": 0.04,
	"--surface-gray-2": 0.08,
	"--surface-gray-3": 0.12,
	"--surface-gray-4": 0.16,
	"--outline-gray-1": 0.15,
	"--outline-gray-2": 0.25,
	"--outline-gray-3": 0.35,
}


# Elevated surfaces (active sidebar item, dock tile, header menu button) are
# lighter than the region, as in Frappe: near-white under dark text, a light
# lift under white text. Share of white mixed into the region colour.
class Ink(StrEnum):
	LIGHT = "Light"
	DARK = "Dark"


CHIP_TOKEN = "--surface-elevation-3"
REGION_ELEVATIONS = {
	"--surface-elevation-2": {Ink.LIGHT: 0.1, Ink.DARK: 0.5},
	CHIP_TOKEN: {Ink.LIGHT: 0.14, Ink.DARK: 0.7},
}

# Ink steps: starting share of text colour, and the contrast each must reach
# on both the region and the chip. Steps 1-3 are decorative (disabled,
# dividers), so unchecked.
REGION_INK = {
	"1": (0.2, None),
	"2": (0.3, None),
	"3": (0.45, None),
	"4": (0.6, colors.WCAG_AA_UI),
	"5": (0.75, colors.WCAG_AA_TEXT),
	"6": (0.82, colors.WCAG_AA_TEXT),
	"7": (0.9, colors.WCAG_AA_TEXT),
	"8": (0.95, colors.WCAG_AA_TEXT),
	"9": (1.0, colors.WCAG_AA_TEXT),
}
INK_SHARE_STEP = 0.01

# Legacy tokens are resolved once at :root; re-resolve them in the region.
REGION_ALIASES = {
	"--text-color": "var(--ink-gray-8)",
	"--heading-color": "var(--ink-gray-9)",
	"--text-muted": "var(--ink-gray-6)",
	"--text-light": "var(--ink-gray-5)",
	"--placeholder-color": "var(--ink-gray-5)",
	"--border-color": "var(--outline-gray-1)",
	"--fg-hover-color": "var(--surface-gray-2)",
	"--dock-ink": "var(--ink-gray-5)",
	"--dock-ink-hover": "var(--ink-gray-7)",
	"--dock-ink-active": "var(--ink-gray-8)",
}
REGION_TOKENS = (
	*REGION_SURFACES,
	*REGION_ELEVATIONS,
	*(f"--ink-gray-{step}" for step in REGION_INK),
	*REGION_ALIASES,
)


@dataclass(frozen=True)
class Brand:
	accent: str | None = None
	sidebar: str | None = None
	dock: str | None = None
	topbar: str | None = None


@dataclass(frozen=True)
class ThemeConfig:
	palette: Palette
	brands: dict[Scheme, Brand]


def current_css() -> str:
	"""CSS for the saved settings. Cached doc, so no query per request."""
	return build_css(from_settings(frappe.get_cached_doc(SETTINGS_DOCTYPE)))


def from_settings(doc) -> ThemeConfig:
	brands = {scheme: _brand(doc, scheme) for scheme in Scheme}
	return ThemeConfig(palette=Palette(doc.neutral_palette or Palette.SLATE), brands=brands)


def build_css(config: ThemeConfig) -> str:
	blocks = [_scheme_block(config, scheme) for scheme in Scheme]
	blocks += _region_blocks(config)
	return "/* Generated from Desk Theme Settings. */\n\n" + "\n\n".join(blocks) + "\n"


def region_tokens(background: str, dark_ink: str) -> dict[str, str]:
	"""Tokens that keep text readable on a region painted `background`.

	Text is white or `dark_ink`, whichever reads better; every ink step that
	carries text is pushed toward it until it clears AA on both the region
	and its active chip.
	"""
	ink = colors.most_readable(background, (WHITE, dark_ink))
	tokens = {name: colors.mix(ink, background, share) for name, share in REGION_SURFACES.items()}
	tokens |= {name: colors.mix(WHITE, background, _elevation_share(name, ink)) for name in REGION_ELEVATIONS}
	surfaces = (background, tokens[CHIP_TOKEN])
	floor = 0.0

	# Ascending, never below the previous step: ink-gray-9 stays the strongest.
	for step, (share, target) in REGION_INK.items():
		floor = _readable_share(ink, background, max(share, floor), target, surfaces)
		tokens[f"--ink-gray-{step}"] = colors.mix(ink, background, floor)

	return tokens | REGION_ALIASES


def find_problems(config: ThemeConfig) -> list[str]:
	"""Human-readable reasons the config is unusable. Empty means valid."""
	problems = []

	for scheme, brand in config.brands.items():
		problems += _scheme_problems(config.palette, scheme, brand)

	return problems


def grays(palette: Palette, scheme: Scheme) -> dict[str, str]:
	"""Frappe's grey ramp for `scheme`, tinted by `palette`."""
	ramp = FRAPPE_GRAYS[scheme]
	if palette == Palette.NEUTRAL:
		return dict(ramp)

	hue, saturation = PALETTE_TINTS[palette]
	return {shade: colors.tint(value, hue, saturation) for shade, value in ramp.items()}


def _brand(doc, scheme: Scheme) -> Brand:
	suffix = FIELD_SUFFIX[scheme]
	return Brand(
		accent=doc.get(f"accent_color{suffix}") or None,
		sidebar=doc.get(f"sidebar_color{suffix}") or None,
		dock=doc.get(f"dock_color{suffix}") or None,
		topbar=doc.get(f"topbar_color{suffix}") or None,
	)


def _scheme_block(config: ThemeConfig, scheme: Scheme) -> str:
	brand = config.brands[scheme]
	ramp = grays(config.palette, scheme)
	properties = {}

	# Neutral keeps Frappe's own greys: emit nothing rather than a copy.
	if config.palette != Palette.NEUTRAL:
		properties.update({f"--gray-{shade}": value for shade, value in ramp.items()})

	properties.update(
		{
			"--desk-theme-accent": _css_value(brand.accent),
			"--desk-theme-accent-fg": _accent_text(brand.accent, ramp),
			"--desk-theme-sidebar": _css_value(brand.sidebar),
			"--desk-theme-dock": _css_value(brand.dock),
			"--desk-theme-topbar": _css_value(brand.topbar),
		}
	)

	return _rule(SCHEME_SELECTORS[scheme], properties)


def _region_blocks(config: ThemeConfig) -> list[str]:
	"""Scoped ink rules for custom-coloured regions, plus the menu reset."""
	blocks = []

	for scheme, brand in config.brands.items():
		dark_ink = grays(config.palette, scheme)["950"]

		for region, value in _region_colors(brand).items():
			if not value:
				continue

			selector = ",\n".join(f"{SCHEME_SCOPE[scheme]} {s}" for s in REGION_SELECTORS[region])
			blocks.append(_rule(selector, region_tokens(colors.normalize(value), dark_ink)))

	if not blocks:
		return []

	# Save the page's values on <html> so menus inside a region can restore them.
	saved = {f"{ROOT_COPY_PREFIX}{name[2:]}": f"var({name})" for name in REGION_TOKENS}
	restored = {name: f"var({ROOT_COPY_PREFIX}{name[2:]})" for name in REGION_TOKENS}
	menus = ",\n".join(
		f"{selector} :is({REGION_MENUS})" for selectors in REGION_SELECTORS.values() for selector in selectors
	)

	return [_rule("html:root", saved), *blocks, _rule(menus, restored)]


def _region_colors(brand: Brand) -> dict[Region, str | None]:
	return {Region.SIDEBAR: brand.sidebar, Region.DOCK: brand.dock, Region.TOPBAR: brand.topbar}


def _rule(selector: str, properties: dict[str, str]) -> str:
	body = "\n".join(f"\t{name}: {value};" for name, value in properties.items())
	return f"{selector} {{\n{body}\n}}"


def _elevation_share(name: str, ink: str) -> float:
	tone = Ink.LIGHT if ink == WHITE else Ink.DARK
	return REGION_ELEVATIONS[name][tone]


def _readable_share(
	ink: str, background: str, share: float, target: float | None, surfaces: tuple[str, ...]
) -> float:
	"""Smallest share >= `share` of `ink` in `background` reaching `target` on every surface."""
	if target is None:
		return share

	while share < 1 and _worst_contrast(colors.mix(ink, background, share), surfaces) < target:
		share = min(1.0, round(share + INK_SHARE_STEP, 2))

	return share


def _worst_contrast(color: str, surfaces: tuple[str, ...]) -> float:
	return min(colors.contrast(color, surface) for surface in surfaces)


def _css_value(value: str | None) -> str:
	if not value:
		return UNSET

	return colors.normalize(value)


def _accent_text(accent: str | None, ramp: dict[str, str]) -> str:
	"""White or near-black, whichever reads better on the accent."""
	if not accent:
		return UNSET

	return colors.most_readable(accent, (WHITE, ramp["950"]))


def _scheme_problems(palette: Palette, scheme: Scheme, brand: Brand) -> list[str]:
	ramp = grays(palette, scheme)
	page = ramp[PAGE_SHADE[scheme]] if PAGE_SHADE[scheme] else WHITE
	problems = []

	# Accent is drawn on the page (links, outlines), so it must contrast with it.
	if brand.accent:
		problems += _hex_problems(scheme, _("Accent"), brand.accent)

	if brand.accent and not problems:
		ratio = colors.contrast(brand.accent, page)
		if ratio < colors.WCAG_AA_TEXT:
			problems.append(
				_(
					"{0} Accent colour {1} has {2}:1 contrast with the page background. It needs {3}:1."
				).format(scheme, brand.accent, round(ratio, 2), colors.WCAG_AA_TEXT)
			)

	# Regions pick their own text colour; only a mid-tone defeats both choices.
	for region, value in _region_colors(brand).items():
		if not value:
			continue

		hex_problems = _hex_problems(scheme, _(region), value)
		if hex_problems:
			problems += hex_problems
			continue

		tokens = region_tokens(colors.normalize(value), ramp["950"])
		strongest = tokens["--ink-gray-9"]
		if _worst_contrast(strongest, (value, tokens[CHIP_TOKEN])) >= colors.WCAG_AA_TEXT:
			continue

		problems.append(
			_("{0} {1} colour {2} is too mid-tone: no text colour reaches {3}:1 on it.").format(
				scheme, _(region), value, colors.WCAG_AA_TEXT
			)
		)

	return problems


def _hex_problems(scheme: Scheme, label: str, value: str) -> list[str]:
	if colors.is_hex(value):
		return []

	return [_("{0} {1} colour {2} is not a hex colour.").format(scheme, label, escape_html(value))]
