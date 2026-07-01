# Kaapana Keycloak theme

Custom login theme (`kaapana`) baked into the Keycloak image. Modern Material
(Vuetify) look, self-contained (no external fonts/CDN — works air-gapped), with
light/dark support and deployment-provided branding.

## Files (this `docker/` context → baked into `/opt/keycloak/themes/kaapana/login/`)

| Source (`files/…`)            | In theme                    | Purpose |
|-------------------------------|-----------------------------|---------|
| `template.ftl`                | `login/template.ftl`        | Layout macro `registrationLayout`: `<head>`, card, logo row, branding header/subheader/notice, separator, page-title, message alert, nested sections, bg canvas + scripts |
| `login.css`                   | `login/resources/css/login.css` | All styling (the single source of truth) |
| `login.ftl`                   | `login/login.ftl`           | Sign-in form (floating-label fields, password toggle, ripple) |
| `login-update-password.ftl`, `login-reset-password.ftl`, `login-otp.ftl` | same names | Floating-label overrides of those flows |
| `js/bg-animation.js`          | `login/resources/js/`       | Animated medical-imaging background (tinted icons, honors `prefers-reduced-motion`) |
| `img/kaapana-logo.png`, `img/icons/*`, `img/favicon.ico` | `login/resources/img/` | Logo, animation icons, favicon (brain + key) |
| `theme.properties` (generated in Dockerfile) | `login/theme.properties` | `parent=keycloak`, `styles=css/login.css`, and the `kaapana*` branding keys fed from `${env.*}` |

Everything else (widgets, JS libs, i18n, unlisted flows) is **inherited** from the
parent `keycloak` → `base` theme.

## How it fits together

- **Activation:** the realm must set `loginTheme: "kaapana"` — done in
  `keycloak-setup/.../realm_objects/kaapana-realm.json` (applied idempotently by
  `configure_realm.py`). Without it the theme is baked but never shown.
- **Deployment branding:** `theme.properties` maps env vars to properties, e.g.
  `kaapanaLoginHeader=${env.KC_LOGIN_HEADER:}`. `template.ftl` reads them as
  `${properties.kaapanaLoginHeader!''}`. The env vars come from
  `keycloak-chart` `deployment.yaml` ← `global.login_*` ← kaapanactl / Helm.
  Empty ⇒ that element is hidden. Institution logo accepts a URL or a `data:` URI.
- **Resources are versioned by Keycloak version, not content:** the served path
  (`/auth/resources/<hash>/login/kaapana/…`) does NOT change when you rebuild the
  theme, so browsers serve stale CSS/JS — **always hard-refresh** after a redeploy.

## Theming gotchas (learned the hard way)

1. **PatternFly is loaded first, our `login.css` last** — so equal-specificity
   rules win for us, but PatternFly's *more specific* selectors do not. Watch for:
   - `.pf-c-form-control:not(textarea) { height: … }` — a bare `.pf-c-form-control`
     height is **ignored**; match the `:not(textarea)` selector.
   - Invalid fields: PatternFly paints a red exclamation via `background-image`.
     Our `background: transparent` shorthand reset `background-repeat`, so the icon
     **tiled**. We now force `background: transparent !important` on `[aria-invalid]`
     and show errors as a border + helper text.
2. **Bootstrap (patternfly-v3) base rules bleed in:**
   - `label { font-weight: 700 }` → floating labels looked bold; we set `font-weight: 400`.
   - `.checkbox` uses `position: absolute; margin-left:-20px` on the input + label
     `padding-left` → flex `gap` did nothing. We reset the checkbox to `position: static`.
3. **`aria-invalid=""`** (empty attribute) still triggers PatternFly's invalid
   styling — emit the attribute only on a real error (`<#if error>aria-invalid="true"</#if>`).
4. **`authChecker.js` API changed** — KC 26.4.6 exports `startSessionPolling` /
   `checkAuthSession` (not `checkCookiesAndSetTimer`). Keep the `<head>` block in
   `template.ftl` in sync with the base template on Keycloak upgrades.
5. **`bg-animation.js` loads at end of `<body>`** (not via `properties.scripts`),
   because it needs the `<canvas>` in the DOM and `window.KAAPANA_ICONS_BASE`
   (set just before it) to resolve `${url.resourcesPath}/img/icons/`.
6. The standalone mockup (`kaapana-login-mockup.zip`) uses the **same `login.css`**
   but has **no PatternFly** — great for design iteration, but always verify the
   real page too, since PatternFly bleed only shows there.

## Field pattern (floating label)

To convert an inherited flow: put the `<input class="pf-c-form-control" placeholder=" ">`
**before** its `<label>` (adjacency drives the float), give the label no class, and
wrap in `.form-group` (position:relative). See `login.ftl` for the canonical field +
password toggle. Verify FreeMarker directive balance and rebuild.

## Rebuild + redeploy (dev loop)

```
docker build -t localhost:5000/keycloak:0.7.0-latest .   # from this docker/ dir
docker push localhost:5000/keycloak:0.7.0-latest
microk8s.kubectl delete pod -n admin -l app.kubernetes.io/name=keycloak,app.kubernetes.io/component=keycloak
# then HARD-REFRESH the browser
```
