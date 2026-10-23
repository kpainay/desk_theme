# Copyright (c) 2026, Orith and contributors
# For license information, please see license.txt

import frappe
from werkzeug.wrappers import Response

from desk_theme.theme import stylesheet

CSS_MIMETYPE = "text/css"

# Revalidate on every load: settings changes show on the next reload, and an
# unchanged theme costs a 304 via the ETag.
CACHE_CONTROL = "no-cache"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def stylesheet_css() -> Response:
	"""Theme colours from `Desk Theme Settings`, as CSS custom properties.

	Guest-readable because the login and website pages load it too. Linked
	from hooks.py (app_include_css / web_include_css).
	"""
	response = Response(stylesheet.current_css(), mimetype=CSS_MIMETYPE)
	response.headers["Cache-Control"] = CACHE_CONTROL
	response.add_etag()
	return response.make_conditional(frappe.request)
