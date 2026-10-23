# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from desk_theme.theme import stylesheet


class DeskThemeSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accent_color: DF.Color | None
		accent_color_dark: DF.Color | None
		dock_color: DF.Color | None
		dock_color_dark: DF.Color | None
		neutral_palette: DF.Literal["Slate", "Zinc", "Neutral"]
		sidebar_color: DF.Color | None
		sidebar_color_dark: DF.Color | None
		topbar_color: DF.Color | None
		topbar_color_dark: DF.Color | None
	# end: auto-generated types

	def validate(self):
		# Block colours that would make text unreadable (WCAG AA).
		problems = stylesheet.find_problems(stylesheet.from_settings(self))
		if not problems:
			return

		frappe.throw("<br>".join(problems), title=_("Theme colours fail contrast"))
