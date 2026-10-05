# Ashfall site deployment — live since 2 October 2026, 07:43 BST

Public URL: **https://ashfall.teknetik.co** (reading open to everyone; sign-up to post, no invite code — Carl's choice).
Taken over from the Hermes cards (t_a747551f, t_6380548f, t_1c1c5310, board Ashfall) by a Claude Code session at
Carl's request on 1 Oct.

## What is live

| Item | State |
| --- | --- |
| Release | `20261001-5a654e6855de` (tarball SHA-256 `707a10efc1acd9c64df4906c8bc09643c91603b709716adaa9d12fba4d359f10`), `/srv/ashfall-promo/current` → `/srv/ashfall-promo/releases/20261001-5a654e6855de`. Earlier releases `161ea4226279` (never to be used: CLI no-op defect) and `71e52123197f` are unpacked beside it. |
| Review | Independent security **PASS** and QA **PASS** for exactly this release: addenda at the end of `../evidence/security/REVIEW-20261001-161ea4226279.md` and `../evidence/qa/QA-20261001-161ea4226279.md` (file names kept by the reviewer's write allowlist), evidence in `../evidence/qa/20261001-161ea4226279/5a654e6855de/`. |
| Service | `ashfall-promo.service` (user `ashfall-promo`), `127.0.0.1:3187` only, `systemd-analyze security` 1.1 OK. |
| Config | `/etc/ashfall-promo/app.env`: template values, plus `ASHFALL_CLIENT_IP_HEADER=x-ashfall-client-ip` and `ASHFALL_SIGNUP_PER_IP_HOUR=40` (interim, see "Client addresses"). Signup open, no invite code. |
| Data / backups | `/var/lib/ashfall-promo/community.sqlite`; `ashfall-promo-backup.timer` daily 03:17 to `/backup/hdd/ashfall-promo` (7 daily + 4 weekly). Backups are single self-contained files and verify `integrity: ok` on this host. |
| TLS | The `teknetik.co` lineage covers exactly apex, www, phone and ashfall (Let's Encrypt, existing account, webroot; expires 30 Dec 2026). The deploy hook `/usr/local/sbin/teknetik-deploy-certificate` expects those four names and renews with the existing timer. |
| Kong | `ashfall-promo` service → `127.0.0.1:3187`, route `ashfall-promo-https` (`ashfall.teknetik.co`, HTTPS only, preserve host, 16 KB request limit, `X-Ashfall-Client-IP` overwritten with the TCP peer). Host guard admits `ashfall.teknetik.co` in Host and SNI. Container-visible files match the host files. |
| HTTP | Port 80 block for `ashfall.teknetik.co`: ACME challenge, everything else 308 → HTTPS. |
| Source of truth | `~/code/teknetik-ai/deploy/kong/single-site.yaml` now equals the live config (uncommitted), so `go-live.py --only kong` reports "already installed". |

## Verification at go-live

- `kong_swap.py --apply` (second run, 07:42:53): teknetik.co 200, www 308, phone 404, /admin 200, /admin/api/summary 401,
  /administrator 404, ashfall / 200, /development 200, /api/health 200, unknown SNI 421 — all with real TLS checks.
  The first run (07:42:25) rolled itself back: its /admin check looked for "Open your customer desk", which teknetik-ai
  commit `388a94a` removed from that page. The check now looks for the page title "Customer desk".
- Off-network fetch of `/development` (from Anthropic's fetch service): page and all five sections served.
- Public end-to-end (`deploy-20261001/public_e2e.mjs`, real DNS + TLS): 5/5 — pages load; disposable sign-up with
  `__Host-` Secure/HttpOnly/SameSite=Lax host-only cookie; post; post and session survive an app-only restart; post
  deleted; account deleted and can't sign in. Database afterwards: 0 users, 0 posts. No errors, 5xx or 429 in the journal.
- HTTP `http://ashfall.teknetik.co/development` → 308 to HTTPS.
- Evidence: `../evidence/deploy/20261002/` (served certificate, live and container config hashes, health, capture).

## Client addresses (deployment gate D1) — partly met

A passive loopback capture (`deploy-20261001/client_ip_tap.py`, request line and one header only) showed:

- Forged `X-Ashfall-Client-IP: 6.6.6.6` / `7.7.7.7` and `X-Forwarded-For` from a client never reach the app: Kong
  replaces the header. **Spoofing a rate-limit bucket is not possible.**
- But both a LAN request and an off-network request reached Kong from **192.168.50.1**, the router: the router rewrites
  the source address of port-forwarded connections. So every public visitor shares one bucket, and the per-IP limits
  act site-wide: page requests 600/min (images and CSS are not counted), sign-ups 40/h (also the fixed global cap),
  logins 20 per 15 min, POSTs 120/min. One abusive client can exhaust a window for everyone.
- Fix options for Carl: stop the router masquerading inbound port-forwards (router NAT/"NAT loopback" setting; affects
  every forwarded port, so check the other services), after which the existing Kong rule gives real addresses with no
  further change. Cloudflare proxying alone doesn't solve it safely, because the origin can't tell Cloudflare's
  connections from direct ones while everything arrives from the router.

## Rollback

- Kong: `sudo install -m 640 -o root -g root /var/lib/ashfall-promo-deploy/20261002T074253Z/{single-site.yaml,host-guard.conf} /etc/kong-single-site/` then `sudo systemctl restart kong-single-site` (wait for no call on :18744). Also restore `teknetik-ai/deploy/kong/single-site.yaml` from git.
- App only: `ln -sfn` `current` to an earlier release and restart, or `sudo systemctl disable --now ashfall-promo.service ashfall-promo-backup.timer`.
- HTTP block and cert hook: originals in `/var/lib/ashfall-promo-deploy/20261001T215809Z-http01-hook/`. Keep the hook
  and the certificate's name set matching (four names now).
- `app.env` before the sign-up change: `/var/lib/ashfall-promo-deploy/20261002T074253Z/app.env`.

## Operating

See `../app/RUNBOOK.md`. First moderator: create an account on the site, then
`ash grant-moderator <username>` with the runbook's `ash` helper.

## Follow-ups

- Router masquerading (above).
- teknetik-ai `go-live.py` still expects "Open your customer desk" on /admin (website step and Kong probes), so its own
  run reports a failing probe until that text is updated.
- Polish: the timeline intro's pause is exactly 12–25 Sep (QA note); "11 to 25" is a day early.
- `content/SOURCE_INVENTORY.md` §5 has no rows yet for `Consciousness Transfer Arc.md` spoilers.
