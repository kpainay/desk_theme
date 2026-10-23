# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

import re
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from desk_theme.theme import colors, stylesheet
from desk_theme.theme.api import stylesheet_css
from desk_theme.theme.stylesheet import Brand, Palette, Scheme, ThemeConfig

BLANK = Brand(accent=None, sidebar=None, topbar=None)
DEFAULT_LIGHT_ACCENT = "#4F5D95"
DEFAULT_DARK_ACCENT = "#8C9AD6"
LOW_CONTRAST = "#cccccc"
DARK_SURFACE = "#333333"
TEAL = "#00998c"
MID_TONE = "#777777"
NEAR_BLACK = "#0c0e12"
GRAY_PATTERN = re.compile(r"--gray-(\d+):\s*(#[0-9a-fA-F]{6});")
DARK_BLOCK_MARKER = '\n[data-theme="dark"]'


def _config(light: Brand = BLANK, dark: Brand = BLANK, palette: Palette = Palette.SLATE) -> ThemeConfig:
	return ThemeConfig(palette=palette, brands={Scheme.LIGHT: light, Scheme.DARK: dark})


def _block(css: str, scheme: Scheme) -> str:
	# Light block comes first, dark second (see build_css).
	light, dark = css.split(stylesheet.SCHEME_SELECTORS[Scheme.DARK], 1)
	return light if scheme == Scheme.LIGHT else dark


class TestColors(UnitTestCase):
	def test_normalize_expands_short_hex(self):
		self.assertEqual(colors.normalize("#ABC"), "#aabbcc")

	def test_normalize_rejects_non_hex(self):
		with self.assertRaises(ValueError):
			colors.normalize("red")

	def test_contrast_black_on_white_is_21(self):
		self.assertAlmostEqual(colors.contrast("#000000", "#ffffff"), 21.0, places=2)

	def test_tint_keeps_grey_lightness_close(self):
		# Tinting must not change readability much: same grey, near-same contrast.
		tinted = colors.tint("#7c7c7c", 215, 0.2)
		self.assertNotEqual(tinted, "#7c7c7c")
		self.assertAlmostEqual(colors.contrast(tinted, "#7c7c7c"), 1.0, delta=0.1)

	def test_most_readable_picks_white_on_dark(self):
		self.assertEqual(colors.most_readable("#1f2937", ("#ffffff", "#0f0f0f")), "#ffffff")

	def test_mix_halfway(self):
		self.assertEqual(colors.mix("#000000", "#ffffff", 0.5), "#808080")


class TestStylesheet(UnitTestCase):
	def test_frappe_grays_match_frappe_source(self):
		# Fails when `bench update` changes Frappe's grey ramp: update FRAPPE_GRAYS.
		source = Path(frappe.get_app_path("frappe", "public", "css", "espresso", "colors.css")).read_text()
		light, dark = source.split(DARK_BLOCK_MARKER, 1)

		for scheme, block in ((Scheme.LIGHT, light), (Scheme.DARK, dark)):
			found = {shade: value.lower() for shade, value in GRAY_PATTERN.findall(block)}
			self.assertEqual(found, stylesheet.FRAPPE_GRAYS[scheme])

	def test_blank_brand_is_unset_in_both_schemes(self):
		# `initial` makes theme.css fall back to Frappe, and stops light leaking into dark.
		css = stylesheet.build_css(_config(light=Brand(DEFAULT_LIGHT_ACCENT, None, None)))
		self.assertIn("--desk-theme-accent: #4f5d95;", _block(css, Scheme.LIGHT))
		self.assertIn("--desk-theme-accent: initial;", _block(css, Scheme.DARK))
		self.assertIn("--desk-theme-sidebar: initial;", _block(css, Scheme.LIGHT))

	def test_neutral_palette_keeps_frappe_greys(self):
		css = stylesheet.build_css(_config(palette=Palette.NEUTRAL))
		self.assertNotIn("--gray-", css)

	def test_slate_palette_tints_greys(self):
		css = stylesheet.build_css(_config(palette=Palette.SLATE))
		self.assertIn("--gray-950:", _block(css, Scheme.DARK))
		self.assertNotIn("--gray-50: #f8f8f8;", css)

	def test_accent_text_is_readable(self):
		css = stylesheet.build_css(_config(light=Brand(DEFAULT_LIGHT_ACCENT, None, None)))
		self.assertIn("--desk-theme-accent-fg: #ffffff;", _block(css, Scheme.LIGHT))

	def test_defaults_pass_contrast(self):
		config = _config(
			light=Brand(DEFAULT_LIGHT_ACCENT, None, None), dark=Brand(DEFAULT_DARK_ACCENT, None, None)
		)
		self.assertEqual(stylesheet.find_problems(config), [])

	def test_low_contrast_accent_is_flagged(self):
		problems = stylesheet.find_problems(_config(light=Brand(LOW_CONTRAST, None, None)))
		self.assertEqual(len(problems), 1)
		self.assertIn("Accent", problems[0])

	def test_region_ink_is_readable_on_teal(self):
		# Reported case: Frappe's ink-gray-6 labels were unreadable on a #00998c sidebar.
		tokens = stylesheet.region_tokens(TEAL, NEAR_BLACK)
		for shade in ("5", "6", "7", "8", "9"):
			self.assertGreaterEqual(colors.contrast(tokens[f"--ink-gray-{shade}"], TEAL), colors.WCAG_AA_TEXT)
		self.assertGreaterEqual(colors.contrast(tokens["--ink-gray-4"], TEAL), colors.WCAG_AA_UI)

	def test_region_picks_light_ink_on_dark(self):
		tokens = stylesheet.region_tokens(DARK_SURFACE, NEAR_BLACK)
		self.assertEqual(tokens["--ink-gray-9"], "#ffffff")

	def test_region_active_chip_keeps_text_readable(self):
		for background in (TEAL, DARK_SURFACE):
			tokens = stylesheet.region_tokens(background, NEAR_BLACK)
			chip_contrast = colors.contrast(tokens["--ink-gray-8"], tokens["--surface-elevation-3"])
			self.assertGreaterEqual(chip_contrast, colors.WCAG_AA_TEXT)

	def test_custom_sidebar_scopes_ink_to_sidebar(self):
		css = stylesheet.build_css(_config(light=Brand(sidebar=TEAL)))
		self.assertIn('html:not([data-theme="dark"]) .body-sidebar,', css)
		self.assertNotIn('html[data-theme="dark"] .body-sidebar', css)

		# Menus inside a region get the page's tokens back.
		self.assertIn(".dropdown-menu", css)
		self.assertIn("--ink-gray-8: var(--desk-theme-root-ink-gray-8);", css)

	def test_phone_regions_follow_dock_and_sidebar(self):
		# On phones the dock is the tab bar and the sheet's top row; the sidebar is the sheet.
		css = stylesheet.build_css(_config(light=Brand(sidebar=TEAL, dock=DARK_SURFACE)))
		self.assertIn(
			'html:not([data-theme="dark"]) frappe-mobile-nav.desk-mobile-nav [data-slot="mobile-nav"]', css
		)
		self.assertIn('html:not([data-theme="dark"]) .desk-mobile-sheet-dock', css)
		self.assertIn('html:not([data-theme="dark"]) .es-bottom-sheet:has(.desk-mobile-sheet)', css)

	def test_blank_regions_emit_no_region_rules(self):
		css = stylesheet.build_css(_config(light=Brand(accent=DEFAULT_LIGHT_ACCENT)))
		self.assertNotIn(".body-sidebar", css)
		self.assertNotIn("--desk-theme-root-", css)

	def test_dark_sidebar_in_light_theme_is_accepted(self):
		# Text adapts to the sidebar, so a dark sidebar is valid in light mode.
		self.assertEqual(stylesheet.find_problems(_config(light=Brand(sidebar=DARK_SURFACE))), [])

	def test_mid_tone_sidebar_is_flagged(self):
		# Neither light nor dark text reaches 4.5:1 on this grey.
		problems = stylesheet.find_problems(_config(light=Brand(sidebar=MID_TONE)))
		self.assertEqual(len(problems), 1)
		self.assertIn("Sidebar", problems[0])

	def test_dock_and_sidebar_are_separate(self):
		# Dock (icon rail) and sidebar (panel) are two components with their own colours.
		css = stylesheet.build_css(_config(light=Brand(sidebar="#eef1f5", dock="#e2e8f0")))
		self.assertIn("--desk-theme-sidebar: #eef1f5;", _block(css, Scheme.LIGHT))
		self.assertIn("--desk-theme-dock: #e2e8f0;", _block(css, Scheme.LIGHT))
		self.assertIn("--desk-theme-dock: initial;", _block(css, Scheme.DARK))

	def test_mid_tone_dock_is_flagged(self):
		problems = stylesheet.find_problems(_config(light=Brand(dock=MID_TONE)))
		self.assertEqual(len(problems), 1)
		self.assertIn("Dock", problems[0])

	def test_invalid_hex_is_flagged(self):
		problems = stylesheet.find_problems(_config(light=Brand(None, None, "<b>red</b>")))
		self.assertEqual(len(problems), 1)
		self.assertNotIn("<b>", problems[0])


class TestThemeSettings(IntegrationTestCase):
	def tearDown(self):
		# Rollback undoes the row, not the Redis doc cache the endpoint reads.
		frappe.db.rollback()
		frappe.clear_document_cache(stylesheet.SETTINGS_DOCTYPE, stylesheet.SETTINGS_DOCTYPE)

	def test_low_contrast_save_is_rejected(self):
		settings = frappe.get_doc(stylesheet.SETTINGS_DOCTYPE)
		settings.accent_color = LOW_CONTRAST
		self.assertRaises(frappe.ValidationError, settings.save)

	def test_endpoint_serves_saved_colours(self):
		settings = frappe.get_doc(stylesheet.SETTINGS_DOCTYPE)
		settings.accent_color = "#3B5B8C"
		settings.save()

		frappe.local.request = Request(EnvironBuilder(method="GET").get_environ())
		response = stylesheet_css()

		self.assertEqual(response.mimetype, "text/css")
		self.assertIn("--desk-theme-accent: #3b5b8c;", response.get_data(as_text=True))

	def test_dock_setting_reaches_stylesheet(self):
		settings = frappe.get_doc(stylesheet.SETTINGS_DOCTYPE)
		settings.dock_color = "#e2e8f0"
		settings.dock_color_dark = "#0b0f14"
		settings.save()

		css = stylesheet.current_css()
		self.assertIn("--desk-theme-dock: #e2e8f0;", _block(css, Scheme.LIGHT))
		self.assertIn("--desk-theme-dock: #0b0f14;", _block(css, Scheme.DARK))
