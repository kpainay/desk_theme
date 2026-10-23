# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

"""Colour math for the theme: hex parsing, hue tinting and WCAG contrast.

Pure functions on "#rrggbb" strings. No Frappe imports, so the rest of the
theme works with colour names, not channel arithmetic.
"""

import colorsys
import re

# "#abc" or "#aabbcc", case-insensitive.
HEX_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
CHANNEL_MAX = 255
DEGREES = 360

# WCAG 2.x relative luminance constants (sRGB linearisation + channel weights).
SRGB_LINEAR_THRESHOLD = 0.04045
SRGB_LINEAR_DIVISOR = 12.92
SRGB_GAMMA_OFFSET = 0.055
SRGB_GAMMA_DIVISOR = 1.055
SRGB_GAMMA = 2.4
LUMINANCE_WEIGHTS = (0.2126, 0.7152, 0.0722)
CONTRAST_FLARE = 0.05

# WCAG 2.x AA minimums: body text, and non-text UI such as icons (1.4.11).
WCAG_AA_TEXT = 4.5
WCAG_AA_UI = 3.0


def is_hex(value: str) -> bool:
	return bool(HEX_PATTERN.match(value or ""))


def normalize(value: str) -> str:
	"""Expand to lowercase "#rrggbb". e.g. "#ABC" -> "#aabbcc"."""
	if not is_hex(value):
		raise ValueError(f"Not a hex colour: {value!r}")

	digits = value[1:].lower()
	if len(digits) == 3:
		digits = "".join(d * 2 for d in digits)

	return f"#{digits}"


def tint(value: str, hue: float, saturation: float) -> str:
	"""Recolour a grey to `hue` (degrees) at `saturation` (0-1), keeping lightness.

	Keeping HSL lightness keeps Frappe's grey ramp, so contrast stays close to
	the original. e.g. tint("#f8f8f8", 215, 0.2) -> "#f7f8f9" (slate-ish).
	"""
	red, green, blue = _channels(value)
	_, lightness, _ = colorsys.rgb_to_hls(red, green, blue)
	return _to_hex(colorsys.hls_to_rgb(hue / DEGREES, lightness, saturation))


def contrast(first: str, second: str) -> float:
	"""WCAG contrast ratio, 1.0 (same) to 21.0 (black on white)."""
	lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
	return (lighter + CONTRAST_FLARE) / (darker + CONTRAST_FLARE)


def most_readable(background: str, candidates: tuple[str, ...]) -> str:
	"""Pick the candidate with the highest contrast on `background`."""
	return max(candidates, key=lambda candidate: contrast(background, candidate))


def mix(first: str, second: str, share: float) -> str:
	"""`share` of `first` blended into `second` in sRGB, like CSS color-mix().

	e.g. mix("#000000", "#ffffff", 0.5) -> "#808080".
	"""
	pairs = zip(_channels(first), _channels(second), strict=True)
	return _to_hex(tuple(a * share + b * (1 - share) for a, b in pairs))


def _channels(value: str) -> tuple[float, float, float]:
	digits = normalize(value)[1:]
	return tuple(int(digits[i : i + 2], 16) / CHANNEL_MAX for i in (0, 2, 4))


def _to_hex(channels: tuple[float, float, float]) -> str:
	return "#" + "".join(f"{round(c * CHANNEL_MAX):02x}" for c in channels)


def _luminance(value: str) -> float:
	linear = [_linearize(c) for c in _channels(value)]
	return sum(weight * c for weight, c in zip(LUMINANCE_WEIGHTS, linear, strict=True))


def _linearize(channel: float) -> float:
	if channel <= SRGB_LINEAR_THRESHOLD:
		return channel / SRGB_LINEAR_DIVISOR

	return ((channel + SRGB_GAMMA_OFFSET) / SRGB_GAMMA_DIVISOR) ** SRGB_GAMMA
