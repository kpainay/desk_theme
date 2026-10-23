(() => {
	// Computed colours of the themed parts, plus pass/fail checks against the tokens.
	const root = getComputedStyle(document.documentElement);
	const v = (name) => root.getPropertyValue(name).trim();
	const el = (sel) => document.querySelector(sel);
	const bg = (sel) => (el(sel) ? getComputedStyle(el(sel)).backgroundColor : null);

	// Resolve a CSS colour expression to rgb() via a probe element.
	const probe = document.createElement("div");
	document.body.appendChild(probe);
	const rgb = (expr) => { probe.style.backgroundColor = ""; probe.style.backgroundColor = expr; return getComputedStyle(probe).backgroundColor; };


	// WCAG contrast between two rgb() strings. Used to prove two surfaces read apart.
	const MIN_SURFACE_STEP = 1.1;
	const WCAG_AA_TEXT = 4.5;
	// rgb() channels are 0-255; color(srgb ...) channels are 0-1.
	const channels = (c) => { const n = c.match(/[\d.]+/g).slice(0, 3).map(Number); return c.startsWith("color(") ? n : n.map((x) => x / 255); };
	const lum = (c) => { const [r, g, b] = channels(c).map((x) => { return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
	const contrast = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };

	const values = {
		theme: document.documentElement.getAttribute("data-theme"),
		mode: document.documentElement.getAttribute("data-theme-mode"),
		primary: rgb("var(--primary)"),
		page: bg("body"),
		sidebar: bg(".body-sidebar"),
		dock: bg(".dock"),
		page_head: bg(".page-head"),
		solid_button: bg('.es-button[data-variant="solid"]:not([data-theme])'),
		modal: bg(".modal.show .modal-content"),
		grid_rows: document.querySelectorAll(".form-grid .grid-row").length,
	};
	const checks = {
		sidebar_uses_token: !el(".body-sidebar") || values.sidebar === rgb("var(--desk-sidebar-bg)"),
		dock_uses_token: !el(".dock") || values.dock === rgb("var(--dock-bg)"),
		dock_differs_from_sidebar: !el(".dock") || contrast(values.dock, values.sidebar) >= MIN_SURFACE_STEP,
		page_head_uses_token: !el(".page-head") || values.page_head === rgb("var(--desk-theme-topbar, var(--bg-color))"),
		// WCAG AA (4.5:1) for every text token on every surface it sits on.
		...Object.fromEntries(
			["--text-color", "--text-muted", "--text-light", "--placeholder-color"].flatMap((t) =>
				["--bg-color", "--control-bg", "--desk-sidebar-bg"].map((s) => [
					`aa${t}_on${s}`,
					contrast(rgb(`var(${t})`), rgb(`var(${s})`)) >= WCAG_AA_TEXT,
				])
			)
		),
		solid_button_is_accent: !values.solid_button || values.solid_button === values.primary,
	};

	// First visible, editable input: hidden tabs and read-only previews can't take focus.
	const editable = (scope) => [...document.querySelectorAll(scope + " input.form-control:not([readonly]):not([disabled])")].find((i) => i.offsetParent);
	const focusTarget = editable(".modal.show") || editable(".frappe-control");
	if (focusTarget) {
		focusTarget.focus({ preventScroll: true });
		values.focus_shadow = getComputedStyle(focusTarget).boxShadow;
		checks.focus_ring_is_accent = values.focus_shadow.includes(rgb("var(--desk-theme-focus)"));
	}

	// Rendered placeholder of a real input, against that input's own background.
	const field = editable(".frappe-control") || editable("");
	if (field) {
		values.placeholder = getComputedStyle(field, "::placeholder").color;
		checks.placeholder_readable = contrast(values.placeholder, getComputedStyle(field).backgroundColor) >= WCAG_AA_TEXT;
	}

	probe.remove();
	return { values, failed: Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k), checks: Object.keys(checks).length };
})()
