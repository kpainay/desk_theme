(() => {
	// Phase 4 targets: values only selectors can reach.
	const root = getComputedStyle(document.documentElement);
	const probe = document.createElement("div");
	document.body.appendChild(probe);
	const resolve = (prop, expr) => { probe.style[prop] = ""; probe.style[prop] = expr; return getComputedStyle(probe)[prop]; };
	const out = { values: {}, failed: [], checks: 0 };
	const check = (name, ok) => { out.checks++; if (!ok) out.failed.push(name); };

	// 1. Floating dock (unpinned + open).
	const dock = document.querySelector(".dock");
	if (dock && !document.body.classList.contains("dock-pinned")) {
		const s = getComputedStyle(dock);
		out.values.dock = { radius: s.borderTopLeftRadius, shadow: s.boxShadow.slice(0, 80), border: `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}` };
		check("dock radius on overlay scale", s.borderTopLeftRadius === resolve("borderTopLeftRadius", "var(--radius-lg)"));
		// Hairline as a ring, not a border: a border would clip the 34px tiles in the 56px tray.
		dock.appendChild(probe);
		const ring = (probe.style.boxShadow = "", probe.style.boxShadow = "0 0 0 1px var(--border-color), var(--shadow-lg)", getComputedStyle(probe).boxShadow);
		probe.remove();
		check("dock hairline ring + lighter shadow", s.boxShadow === ring);
		check("dock tiles not clipped", [...dock.querySelectorAll(".dock-item, .dock-tile, a, button")].every((t) => t.getBoundingClientRect().width <= dock.clientWidth));
	}

	// 2. Child-table cell focus.
	const cell = document.querySelector(".grid-body .editable-row input.form-control:not([readonly])");
	if (cell) {
		cell.focus({ preventScroll: true });
		const shadow = getComputedStyle(cell).boxShadow;
		out.values.grid_focus = shadow;
		check("grid focus ring is accent", shadow.includes(resolve("color", "var(--desk-theme-focus)")));
	}

	// 3. Checked checkbox.
	const box = document.querySelector('.modal.show input[type="checkbox"]:checked, input[type="checkbox"]:checked');
	if (box) {
		const image = getComputedStyle(box).backgroundImage;
		out.values.checkbox = image.slice(-120);
		check("checked checkbox is accent", image.includes(resolve("color", "var(--primary)")));
	}

	probe.remove();
	return out;
})()
