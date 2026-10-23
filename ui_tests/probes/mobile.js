(() => {
	// Phone: the tab bar and the sheet's dock row paint like the dock, the navigation
	// sheet like the sidebar, and every label on them reads at AA.
	const AA = 4.5;
	const probe = document.createElement("div");
	const channels = (c) => { const n = c.match(/[\d.]+/g).slice(0, 3).map(Number); return c.startsWith("color(") ? n : n.map((x) => x / 255); };
	const lum = (c) => { const [r, g, b] = channels(c).map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
	const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return +((hi + 0.05) / (lo + 0.05)).toFixed(2); };
	const page = (expr) => { document.body.appendChild(probe); probe.style.backgroundColor = ""; probe.style.backgroundColor = expr; const c = getComputedStyle(probe).backgroundColor; probe.remove(); return c; };
	const bg = (el) => getComputedStyle(el).backgroundColor;

	const out = { values: { theme: document.documentElement.getAttribute("data-theme") }, failed: [], checks: 0 };
	const check = (name, ok) => { out.checks++; if (!ok) out.failed.push(name); };
	const readable = (name, labels, surface) => {
		const worst = Math.min(...[...labels].filter((l) => l.offsetParent && l.textContent.trim()).map((l) => ratio(getComputedStyle(l).color, surface)));
		out.values[`${name}_worst_text`] = worst;
		check(`${name} text AA`, worst >= AA);
	};

	const bar = document.querySelector('frappe-mobile-nav [data-slot="mobile-nav"]');
	if (bar) {
		out.values.tabbar = bg(bar);
		check("tab bar is dock colour", bg(bar) === page("var(--dock-bg)"));
		readable("tabbar", bar.querySelectorAll("span, a, button"), bg(bar));
	}

	const sheet = document.querySelector(".es-bottom-sheet-root:not([data-state='closed']) .es-bottom-sheet:has(.desk-mobile-sheet)");
	if (sheet) {
		out.values.sheet = bg(sheet);
		check("sheet is sidebar colour", bg(sheet) === page("var(--desk-sidebar-bg)"));
		readable("sheet title", sheet.querySelectorAll(".es-bottom-sheet__title"), bg(sheet));
		readable("sheet sidebar", sheet.querySelectorAll(".desk-mobile-sheet-sidebar .sidebar-item-label"), bg(sheet));

		const row = sheet.querySelector(".desk-mobile-sheet-dock");
		out.values.sheet_dock = bg(row);
		check("sheet dock row is dock colour", bg(row) === page("var(--dock-bg)"));
		readable("sheet dock", row.querySelectorAll(".dock-item-label"), bg(row));
	} else {
		check("navigation sheet opened", false);
	}
	return out;
})()
