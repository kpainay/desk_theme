// UI run over CDP: one headless Chrome, many pages. Each step can switch the
// desk theme, evaluate a probe and save a screenshot.
// usage: ORIGIN=<url> SID=<session> node runner.mjs <plan.json> <out-dir>
// plan: [{ name, url, mode?: light|dark|automatic, os?: light|dark, setup?: js, probe?: js, wait?: ms }]
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { join } from "node:path";

const [planPath, outDir] = process.argv.slice(2);
const plan = JSON.parse(readFileSync(planPath, "utf8"));
const PORT = 9334;
// Site under test, e.g. http://lichen.localhost:8001
const ORIGIN = process.env.ORIGIN || "http://orith.localhost:8003";
const VIEWPORT = { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false };
const DEFAULT_WAIT = 2500;

const profile = mkdtempSync(join(outDir, "chrome-"));
const chrome = spawn("google-chrome", [
	"--headless=new",
	`--remote-debugging-port=${PORT}`,
	`--user-data-dir=${profile}`,
	"--no-first-run",
	"--disable-gpu",
	"about:blank",
]);
process.on("exit", () => chrome.kill());

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pageSocket() {
	for (let i = 0; i < 50; i++) {
		try {
			const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
			const page = targets.find((t) => t.type === "page");
			if (page) return page.webSocketDebuggerUrl;
		} catch {}
		await sleep(200);
	}
	throw new Error("Chrome did not start");
}

const ws = new WebSocket(await pageSocket());
await new Promise((r) => ws.addEventListener("open", r));

let nextId = 0;
const pending = new Map();
const listeners = new Set();
ws.addEventListener("message", (event) => {
	const msg = JSON.parse(event.data);
	if (msg.id && pending.has(msg.id)) {
		pending.get(msg.id)(msg);
		pending.delete(msg.id);
		return;
	}
	listeners.forEach((fn) => fn(msg));
});

const send = (method, params = {}) =>
	new Promise((resolve) => {
		const id = ++nextId;
		pending.set(id, resolve);
		ws.send(JSON.stringify({ id, method, params }));
	});

const evaluate = async (expression) => {
	const res = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
	if (res.result?.exceptionDetails) return { error: res.result.exceptionDetails.exception?.description };
	return res.result?.result?.value;
};

const navigate = async (url) => {
	let done;
	const loaded = new Promise((r) => (done = r));
	const fn = (m) => m.method === "Page.loadEventFired" && done();
	listeners.add(fn);
	await send("Page.navigate", { url: ORIGIN + url });
	await loaded;
	listeners.delete(fn);
};

await send("Page.enable");
await send("Network.enable");
await send("Emulation.setDeviceMetricsOverride", VIEWPORT);
// Headless pages never own window focus, so :focus would never match.
await send("Emulation.setFocusEmulationEnabled", { enabled: true });

if (process.env.SID) {
	await send("Network.setCookie", { name: "sid", value: process.env.SID, url: ORIGIN });
}

// Switch theme the way Frappe does (data-theme-mode + set_theme), without saving it.
const applyMode = (mode) => `(() => {
	document.documentElement.setAttribute("data-theme-mode", "${mode}");
	frappe.ui.set_theme();
	return document.documentElement.getAttribute("data-theme");
})()`;

const results = {};
for (const step of plan) {
	// Per-step viewport, e.g. { width: 390, height: 844, mobile: true } for a phone.
	await send("Emulation.setDeviceMetricsOverride", { ...VIEWPORT, ...(step.viewport || {}) });
	await send("Emulation.setTouchEmulationEnabled", { enabled: !!step.viewport?.mobile });
	await send("Emulation.setEmulatedMedia", {
		features: [{ name: "prefers-color-scheme", value: step.os || "light" }],
	});
	await navigate(step.url);
	await sleep(step.wait ?? DEFAULT_WAIT);

	if (step.mode) await evaluate(applyMode(step.mode));
	if (step.setup) await evaluate(step.setup);
	await sleep(400);

	results[step.name] = step.probe ? await evaluate(step.probe) : null;
	const shot = await send("Page.captureScreenshot", { format: "png" });
	writeFileSync(join(outDir, `${step.name}.png`), Buffer.from(shot.result.data, "base64"));
}

console.log(JSON.stringify(results, null, 1));
ws.close();
process.exit(0);
