# Ashfall promo and tester community site

This is the self-hosted promotional website for Ashfall. It also hosts the early-tester discussion area: accounts, per-topic likes, ideas, feedback and replies. Operating procedures are in [RUNBOOK.md](RUNBOOK.md). The deployment contract is [../ops/PREFLIGHT.md](../ops/PREFLIGHT.md).

## Stack

- **Runtime:** Node.js 26 built-ins only (`node:http`/`https`, `node:sqlite`, `crypto.scrypt`). The runtime has **no npm dependencies**, so a release is just `server/` + `dist/` + `package.json`.
- **Database:** SQLite in WAL mode, with versioned migrations (`server/db.mjs`). The file is created with mode 0600.
- **Pages:** server-rendered with auto-escaping templates (`server/html.mjs`, `server/views.mjs`). The client (`client/site.js`) is progressive enhancement only, so every page and form works without JavaScript.
- **Dev-only dependencies:** Playwright 1.63.0 (it matches the installed Chromium 1243), TypeScript (`checkJs`), ESLint, and @fontsource. The fonts are OFL-licensed and self-hosted; their licences ship in `dist/public/fonts/LICENSES.txt`.

## Layout

```
app/
  server/      index.mjs (entrypoint), app.mjs (routing/security), views.mjs, store.mjs (parameterised SQL),
               db.mjs (migrations), security.mjs (scrypt, rate limits), config.mjs (env), cli.mjs (operator CLI)
  client/      site.css, site.js (built into content-hashed bundles)
  scripts/     build.mjs, e2e.mjs, candidate-manifest.mjs, lib/ (content parser/renderer), shots/walk/elshots (visual review)
  test/        unit/ and integration/ (node:test), helpers.mjs (isolated TLS server + cookie client)
  deploy/      ashfall-promo.service, ashfall-promo-backup.{service,timer}, app.env.example, run-qa.sh
  dist/        build output (git-ignored). Only dist/public is ever served.
  release/     candidate manifest + runtime tarball (git-ignored)
  evidence/    E2E screenshots + reports (git-ignored)
```

The inputs `../content`, `../assets`, `../design` and `../ops` are read-only for this app. The build consumes `content/WEBSITE_COPY.md`, `assets/manifest.json` and `assets/web/*`.

## Commands (app-only; run inside `app/`)

| Command | What it does |
| --- | --- |
| `npm ci` | Install the pinned dev toolchain from `package-lock.json`. |
| `npm run build` | Content and asset build into `dist/`. It strips editorial `> src:` lines, applies content corrections, hash-verifies every web image against the manifest, and **fails** on any spoiler, internal or placeholder text. |
| `npm run lint` | ESLint (flat config), no warnings allowed. |
| `npm run typecheck` | `tsc --noEmit` with `checkJs` over server, client, scripts and tests. |
| `npm test` | Unit tests plus integration tests against the real entrypoint over TLS. Each run uses a fresh temp DB that is then deleted. |
| `npm run test:e2e` | Playwright at desktop 1440×900 and mobile 390×844. Covers the menu focus trap and Escape, gallery filters, keyboard lightbox, capacity explainer, atlas, reduced motion and no-JS. Also runs signup → post → reload → logout → login → like persists. Screenshots and `report.json` go to `evidence/e2e/<UTC>/`. |
| `npm run check` | build + lint + typecheck + test + test:e2e. |
| `npm run manifest` | Writes `dist/RELEASE` and `release/MANIFEST.json`, `release/SHA256SUMS` and `release/ashfall-promo-<id>.tar.gz` (+ `.sha256`). |
| `npm start` | `node server/index.mjs`; it needs the environment described below. |

All tests are isolated from real user data. They spawn the production entrypoint against `mktemp` directories, with a temporary self-signed certificate for `ashfall.teknetik.co`. Test accounts are random (`test/helpers.mjs` `genUser`) and their credentials are never printed or stored.

## Configuration

Configuration comes from the environment only; see [deploy/app.env.example](deploy/app.env.example). It contains no secrets, and no default admin account or password exists. The server refuses to start when any of these hold:
- the origin is not `https://`
- the bind address is not loopback
- `ASHFALL_DB_PATH` is missing
- the scrypt cost is weak

Moderators are granted on the server with `node server/cli.mjs grant-moderator <username>`, applied to an account that already exists.

## Security summary

- **Passwords:** scrypt (N=32768, r=8, p=1, 16-byte salt), with rehash on login when parameters change. The policy is at least 10 characters, rejects common and username-derived passwords, and allows at most 200 characters.
- **Sessions:** 256-bit random tokens, stored server-side as SHA-256 hashes only. The cookie is `__Host-ashfall_session` with `Secure; HttpOnly; SameSite=Lax; Path=/` and no Domain. Sessions last 30 days and are revocable. A password change revokes the account's other sessions.
- **CSRF:** a per-session (or pre-login) token on every form, plus an exact `Origin` match against the configured origin and a `Sec-Fetch-Site` cross-site rejection.
- **Host guard:** wrong `Host` returns 421. Forwarding headers are never trusted. An optional client-IP header is accepted only from a loopback peer, and only if it is a single valid IP.
- **Limits:**
  - 16 KB form bodies (`application/x-www-form-urlencoded` only; anything else gets 415)
  - per-IP request, signup and login limits, plus a per-account login throttle
  - per-user post, like, report and account-action limits
  - a signup honeypot
- **Data handling:** all SQL is parameterised. All output is escaped by default, and posts are plain text with control and bidi characters stripped. Strict CSP (`default-src 'none'`, self-only scripts and styles, no inline code), `frame-ancestors 'none'`, nosniff, and a strict referrer policy.
- **Authorisation:** checked on the server for every mutation. Only the owner may edit or delete a post. Moderation (remove/restore, lock topic, suspend user) requires the server-granted role and is recorded in `mod_log`. Account deletion erases the username, hash, sessions and likes, and replaces post text.
- **Static files:** served from an exact-match map built from `dist/public` only. Content sources, the manifest, originals, ops, the DB and node_modules are unreachable (verified in the integration tests).

## Content honesty

- Every image carries a visible **CONCEPT ART — NOT GAMEPLAY** or **IN BUILD** label, including in the lightbox.
- Planned systems and regions are badged separately from documented build evidence.
- Spoiler terms from the source inventory are rejected by the build.
