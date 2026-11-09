// Phone browser chrome (address/app bar) colour. desk.html hard-codes
// <meta name="theme-color" content="#0089FF">; repaint it with the dock
// colour, which on phones is also the tab bar:
//
//   theme.css --dock-bg ──probe──► rgb ──► meta theme-color
//
// Re-run when Frappe swaps light/dark (data-theme on <html>).
(() => {
	const METAS = ['meta[name="theme-color"]', 'meta[name="msapplication-navbutton-color"]'];

	// --dock-bg may be a color-mix(); let the browser resolve it to pixels.
	function dock_rgb() {
		const probe = document.createElement("div");
		probe.style.cssText = "position:absolute;width:0;height:0;background:var(--dock-bg)";
		document.documentElement.appendChild(probe);
		const color = getComputedStyle(probe).backgroundColor;
		probe.remove();

		const ctx = document.createElement("canvas").getContext("2d");
		ctx.fillStyle = color;
		ctx.fillRect(0, 0, 1, 1);
		const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
		if (!a) {
			return null;
		}
		return `rgb(${r}, ${g}, ${b})`;
	}

	function paint() {
		const color = dock_rgb();
		if (!color) {
			return;
		}

		for (const selector of METAS) {
			let meta = document.querySelector(selector);
			if (!meta) {
				meta = document.createElement("meta");
				meta.name = selector.match(/name="(.+)"/)[1];
				document.head.appendChild(meta);
			}
			meta.content = color;
		}
	}

	paint();
	window.addEventListener("load", paint);
	new MutationObserver(paint).observe(document.documentElement, {
		attributes: true,
		attributeFilter: ["data-theme"],
	});
})();
