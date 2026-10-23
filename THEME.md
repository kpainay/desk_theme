# Desk Theme

Restyles the Frappe desk, login and website pages from one installable app. CSS
variables only where possible; no Frappe files are modified.

## Change the colours

Desk search bar › **Desk Theme Settings** (on orith: Orith workspace › Settings). Reload the page after saving.

| Field | Paints |
|---|---|
| Neutral Palette | Every surface, text and border grey (Slate, Zinc or Frappe's Neutral) |
| Accent | Primary buttons, links, checkboxes, focus rings |
| Sidebar | Desk sidebar (224px panel); on phones, the navigation sheet |
| Dock | Desk dock (icon rail left of the sidebar); on phones, the tab bar and the sheet's app row |
| Top Bar | Desk page header, website navbar |

Light and dark are set separately. Blank means "use the default".

- Save is refused if the accent has less than 4.5:1 contrast with the page (WCAG AA).
- Sidebar, dock and top bar pick their own text colour (white or near-black)
  and keep every text level at AA. Only mid-tone colours, where neither
  works, are refused.
- Default accents (`#4F5D95` light, `#8C9AD6` dark) are the field defaults in
  `desk_theme_settings.json`.

## How it fits together

```
Desk Theme Settings ──validate──► stylesheet.find_problems()
        │
        ▼
desk_theme/theme/stylesheet.py ──► /api/method/desk_theme.theme.api.stylesheet_css
  palette ramp  --gray-50…950                 (guest-readable, ETag, no-cache)
  brand values  --desk-theme-accent, -sidebar, -dock, -topbar
  region rules  ink/hover tokens scoped to sidebar, dock, top bar
        │
        ▼
desk_theme/public/css/theme.css   maps Frappe tokens onto var(--desk-theme-*, <Frappe default>)
```

Both stylesheets load after Frappe's through `app_include_css` and
`web_include_css` in `hooks.py`.

| File | Role |
|---|---|
| `desk_theme/theme/colors.py` | Colour maths: hex, tint, mix, WCAG contrast. No Frappe imports. |
| `desk_theme/theme/stylesheet.py` | Builds the dynamic CSS and validates settings. |
| `desk_theme/theme/api.py` | Serves the dynamic CSS. |
| `desk_theme/public/css/theme.css` | Static token mapping and selector overrides. Sections are numbered; see its header. |
| `desk_theme/theme/test_theme.py` | Unit and integration tests. |

Rules that keep it working:

- Token selectors use `html:root` / `html[data-theme="dark"]`, which outrank
  Frappe's `:root` whatever the load order. The login page loads
  `login.bundle.css` after us, and it re-declares every Frappe token.
- Any token set for light must also be set for dark, or the light value wins
  on `<html>` in dark mode.
- Blank settings are emitted as `initial`, so `var(--desk-theme-x, fallback)`
  falls back to Frappe's value and light colours never leak into dark.
- Website pages never set `data-theme`, so they always render light.
- `/printview` loads only Frappe's print bundle, so printed output is untouched.

## Fragile: re-check after `bench update`

These depend on Frappe internals that variables don't cover.

1. **`theme.css` section 8** (selector overrides). Each rule names its target:
   - `.page-head`, `.navbar-light`: top bar background
   - `.es-button`: solid button colours (`--bt-solid-*`)
   - `.btn.btn-primary`: text on Bootstrap primary buttons
   - `.form-control::placeholder`: placeholder colour (Frappe uses raw greys)
   - `.form-control:focus`, `.grid-body .editable-row .form-control:focus`: focus rings
   - `body:not(.dock-pinned) .dock`: floating dock radius and shadow
   - `frappe-mobile-nav.desk-mobile-nav [data-slot="mobile-nav"]`: phone tab
     bar. The host class is needed to beat the `<style>` frappe-ui injects
     after us with the same selector minus the class.
   - `.desk-mobile-sheet-dock`, `.es-bottom-sheet:has(.desk-mobile-sheet)`:
     the phone navigation sheet (`mobile_nav.js` `open_navigation`)
2. **`stylesheet.py` `REGION_SELECTORS` / `REGION_MENUS`**: the markup each
   region colour scopes to (`.body-sidebar`, `.dock`, `.page-head`,
   `.navbar-light`, and the phone tab bar and navigation sheet) and the menus
   inside them that get page tokens back.
3. **`stylesheet.py` `FRAPPE_GRAYS`**: a copy of Frappe's grey ramp. The test
   `test_frappe_grays_match_frappe_source` fails when Frappe changes it.
4. **Frappe token names overridden in `theme.css`**: `--desk-sidebar-bg`,
   `--dock-bg`, `--checkbox-gradient`, `--card-shadow`, `--primary`,
   `--placeholder-color` and the legacy aliases. A rename in Frappe makes the
   override silently stop working. Grep `apps/frappe/frappe/public` for each.

After an update:

```bash
bench --site <site> run-tests --module desk_theme.theme.test_theme
bench --site <site> run-tests --module desk_theme.theme.test_theme --test-category unit

# run.sh itself (stubs bench and node; no site needed)
apps/desk_theme/ui_tests/test_run.sh <bench-dir>

# Screenshot UI tests (headless Chrome over CDP). Site must be served, redis up.
apps/desk_theme/ui_tests/run.sh <bench-dir> <site> <origin> <workspace-route> <doctype> [out-dir]
apps/desk_theme/ui_tests/run.sh . orith.localhost http://orith.localhost:8003 /app/orith tenant
```

`run.sh` checks every page below in light, dark and automatic (OS light and
dark), at desktop and phone width, with saved, custom and blank colours. It
checks token use, AA contrast, focus rings, dock/sidebar separation and that
each step rendered logged-in in the expected theme. It prints failures and a
total, and writes screenshots plus contact sheets (`sheet_*.png`) to review by
eye. Probes live in `ui_tests/probes/`; `build_plans.py` turns them into plans.

The pages it covers, to also eyeball:

- login page
- workspace (sidebar, pinned and floating dock)
- a list view
- a form with an editable child table
- a dialog with a checked checkbox
- report view
- at phone width (390px): the tab bar, and the navigation sheet (tap the page title)

Things to look for: unreadable text, a grey focus ring where the accent should
be, and a dock that blends into the sidebar.
