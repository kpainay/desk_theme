(() => {
	// Inside each custom-coloured region: ink steps must clear AA on the region and its active chip,
	// and menus inside the region must get the page's text colour back.
	const AA = 4.5, UI = 3.0;
	const probe = document.createElement("div");
	const channels = (c) => { const n = c.match(/[\d.]+/g).slice(0, 3).map(Number); return c.startsWith("color(") ? n : n.map((x) => x / 255); };
	const lum = (c) => { const [r, g, b] = channels(c).map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
	const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return +((hi + 0.05) / (lo + 0.05)).toFixed(2); };
	const resolveIn = (el, expr) => { el.appendChild(probe); probe.style.color = ""; probe.style.color = expr; const c = getComputedStyle(probe).color; probe.remove(); return c; };

	const out = { values: { theme: document.documentElement.getAttribute("data-theme") }, failed: [], checks: 0 };
	const check = (name, ok) => { out.checks++; if (!ok) out.failed.push(name); };

	for (const sel of [".body-sidebar", ".dock", ".page-head"]) {
		const el = document.querySelector(sel);
		if (!el) continue;
		const bg = getComputedStyle(el).backgroundColor;
		const chip = resolveIn(el, "var(--surface-elevation-3)");
		const row = { bg, chip };
		for (const step of [4, 5, 6, 7, 8, 9]) {
			const ink = resolveIn(el, `var(--ink-gray-${step})`);
			const worst = Math.min(ratio(ink, bg), ratio(ink, chip));
			row[`ink${step}`] = worst;
			check(`${sel} ink-gray-${step}`, worst >= (step === 4 ? UI : AA));
		}
		out.values[sel] = row;
	}

	// Menus inside the top bar: same text colour as the page.
	const menu = document.querySelector(".page-head .dropdown-menu");
	if (menu) {
		const pageText = resolveIn(document.body, "var(--text-color)");
		const menuText = resolveIn(menu, "var(--text-color)");
		out.values.menu = { pageText, menuText };
		check("menu text restored", pageText === menuText);
	}
	return out;
})()
