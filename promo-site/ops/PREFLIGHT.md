# Ashfall deployment preflight — 1 October 2026

Task: t_1f3211d4. Board: Ashfall. Workspace: /home/teknetik/code/ao2/promo-site.

## Result and scope

READ-ONLY preflight COMPLETE. Application implementation can proceed against the contract below. PUBLIC DEPLOYMENT IS NOT READY: Ashfall is denied by both ingress host guards and is absent from the current certificate. These are known scoped deployment prerequisites, not missing Docker or DNS credentials. No DNS, firewall, router, Kong, certificate, account, service or Unity changes were made. This card writes only ops/.

Observations were collected from the live host on 1 October 2026, approximately 12:37–12:47 UTC. Recheck before deployment; this is not a reservation or proof of future state. Read PROJECT_BRIEF.md and the domain-dns-operations and teknetik-kong skills. Reviewed both existing child cards: implementation t_96803b8f and deployment t_1c1c5310. Security and QA remain gates on that deployment card.

## 1. Authoritative DNS and capability

- Parent delegation verified by querying a.registrydns.co (discovered from live .co NS): michael.ns.cloudflare.com and sneh.ns.cloudflare.com.
- Both authoritative Cloudflare nameservers and recursive resolvers 1.1.1.1 and 8.8.8.8 answer ashfall.teknetik.co A 92.27.142.6, TTL 300. No AAAA was returned by the initial recursive query.
- Authenticated Cloudflare API GET verified active zone teknetik.co, ID d726890692a9af96b838cbfcd082c618, with the same two nameservers.
- EXACT record exists, not wildcard: ID 0340d31c52af900cc507be48f002f6fc, type A, name ashfall.teknetik.co, content 92.27.142.6, TTL 300, proxied false. Query for *.teknetik.co returned no records.
- Apex record ID 140144e703d669034fcfe79d9534b121 and www record ID 1699de294bf2cdb22892d554644a9082 point at the same origin but are proxied true; preserve them and mail records. Ashfall is currently direct-to-origin and has no Cloudflare WAF protection.
- Credential capability PRESENT: noninteractive 1Password service-account access, Alice vault item CLOUDFLARE_API_KEY. Authenticated reads worked and the zone API reports #dns_records:read and #dns_records:edit. No write was attempted; edit permission reported by the provider is not a tested mutation.
- Credential values were kept in subprocess memory and HTTPS request headers, not output or source. Do not copy credentials into app runtime, browser, logs or env examples.
- Choose NO DNS CHANGE for deployment if these exact values still match the live WAN address. Do not provision a GCP zone, register a domain, change nameservers, add a wildcard or toggle Cloudflare proxying.

## 2. Live ingress, host network and boundaries

Host address 192.168.50.132, default route via 192.168.50.1 on eno1. Read-only key-authenticated router SSH worked with the configured key and strict known-host checking. Router WAN address is 92.27.142.6. Enabled NAT forwards include WAN443 -> host8443 and WAN80 -> host8088. Historical forwards also exist for 8444, 8445 and other ports including 5273; do not reuse 5273 for the app or change unrelated forwards. They are inventory/risk observations, not evidence that those ports are externally reachable.

UFW is active. Relevant ingress rules allow 8088 and 8443 on eno1 from Anywhere, and 18745 from the LAN. No backend exception is required for a loopback app. Do not add app, Admin API or management port exposure.

Unprivileged docker ps fails with socket permission denied. sudo -n docker ps/inspect/exec works safely. No Docker group addition, socket chmod or socket publication is needed or permitted. Sudo noninteractive capability is PRESENT.

Live Kong:

- systemd kong-single-site.service, active/running, container kong-single-site.
- Kong Enterprise 3.13.0.0, image sha256:bb7eb61a020630b0ac6c514532c63c81b2c8726b30e4d84dc755baf65ba885c2.
- Network mode host, no published Docker ports and no container bridge dependency. Host loopback is reachable from Kong.
- DB-less: KONG_DATABASE=off, KONG_DECLARATIVE_CONFIG=/opt/kong/single-site.yaml. Admin, Manager, status, debug, stream, cluster and portal listeners are disabled by the installed unit. No live :8444/:8445 listener appeared in ss.
- Proxy 0.0.0.0:8443 ssl, HTTP handler separately on 0.0.0.0:8088.
- Bind mounts (read-only): /etc/kong-single-site/single-site.yaml -> /opt/kong/single-site.yaml, /etc/kong-single-site/host-guard.conf -> /opt/kong/host-guard.conf, /etc/kong-single-site/tls -> /opt/kong/tls.
- Existing services: teknetik-website -> 192.168.50.132:3000; teknetik-phone -> 127.0.0.1:18744; teknetik-admin-desk -> 127.0.0.1:18745. Preserve all existing routes, plugins, timeouts and behavior.
- Plugin allowlist is pre-function,request-size-limiting. Do not assume gateway rate-limiting/OIDC/acme plugins are enabled; implement app-side rate limiting and username/password auth.
- /etc/kong-single-site/host-guard.conf accepts only teknetik.co, www.teknetik.co and phone.teknetik.co in BOTH Host and SNI, and requires Host/SNI equality. A new route alone will not work.
- HTTP handler /etc/kong-single-site/http01-nginx.conf has those same three names and an exact Host guard, a dedicated webroot challenge handler, default 421, and non-challenge redirect to the apex. Ashfall needs its OWN server block so its HTTP paths redirect to https://ashfall.teknetik.co, not the Teknetik apex.
- The historical Kong RBAC item exists in Alice vault, but its token was not fetched. It is neither necessary nor a working management capability for this Admin-disabled gateway. Do not revive the old public Admin API or DB-backed recovery runtime.

## 3. TLS, approval and renewal

Current presented certificate /etc/kong-single-site/tls/current/fullchain.pem:

- Subject CN teknetik.co, issuer Let's Encrypt YE1.
- SANs exactly phone.teknetik.co, teknetik.co, www.teknetik.co. NO ashfall.teknetik.co and no wildcard.
- Valid 30 September 2026 14:39:16 UTC through 29 December 2026 14:39:15 UTC.
- current symlink target releases/release-9nt4yh1r.
- Source lineage /etc/letsencrypt/live/teknetik.co; renewal file /etc/letsencrypt/renewal/teknetik.co.conf.
- Existing production ACME directory https://acme-v02.api.letsencrypt.org/directory; local account identifier 74fc8045e8cab3cc866939f6ddebe41e. Certificate authenticator webroot, all three names mapped to /var/lib/letsencrypt, key_type ecdsa.
- Renewal kong-single-site-renew.timer is enabled/active with twice-daily schedule and up to one hour random delay. Service invokes certbot renew --cert-name teknetik.co --quiet, then /usr/local/sbin/teknetik-deploy-certificate even when issuance was not due.
- /etc/letsencrypt/renewal-hooks/deploy/teknetik-deploy-certificate resolves to that same installed script.
- Hook fixes LINEAGE to teknetik.co and HOSTS to the exact three existing names; rejects any different SAN set, validates chain/key/expiry, promotes a release symlink, restarts only kong-single-site.service, proves served leaf fingerprints and rolls back on failure.
- Journal shows successful fingerprint reconciliation at 1 October 2026 12:57:39 BST. This is NOT proof of a fresh renewal, Ashfall readiness, or forced production failure/rollback.

Approval evidence recovered from actual boss session 20260930_100247_a56dfb, messages 68608–68610: user explicitly accepted the existing Let's Encrypt Subscriber Agreement at 30 September 2026 09:17:29 UTC in response to a question proposing the owner's business contact. No different address was supplied. Historical comment pointed to teknetik-co t_a3117cd8, but that card could not be found in the current board store; the original conversation is the available evidence. Keep the contact address in the original private history rather than copying it into this runbook/metadata.

Local account regr.json has an empty body and an account URI; it does NOT verify the CA's currently stored contact or retain the ToS acceptance flag. Do not infer those fields from the certificate. Reuse the existing approved production account, do not create a new account/accept different CA terms/update contact merely to publish this site. If Certbot unexpectedly demands a new agreement or an account/contact decision, stop with that precise prerequisite. No ACME call or account mutation was made on this preflight.

### Chosen minimal TLS integration

Extend the EXISTING teknetik.co lineage to the exact four names (all three existing names PLUS ashfall.teknetik.co), using the existing production account and webroot. This avoids a second certificate mount, second timer and bespoke SNI delivery pipeline. It couples Ashfall renewal to the existing three-host lineage, so preservation and rollback testing are mandatory.

Deployment must update the hook's allowed HOSTS/SAN set to all four in the same reviewed transaction; expanding the certificate without the hook change fails promotion. Keep the old certificate/key releases recoverable and root-controlled. Do not print/read private-key values in tools or reports. The deployment card must prepare and review candidate changes under promo-site/ops first, never edit the source project kong-konnect.

Sequence: stage the Ashfall-only HTTP challenge/redirect server block and validate nginx; obtain a unique harmless token from genuinely OFF-LAN for all four hostnames before any issuance; remove the token afterward. Current Ashfall challenge requests are 421. A missing-token 404 for the existing apex proves handler selection only, not external reachability. Run isolated staging/dry-run issuance as appropriate with staging data kept separate; then expand production lineage using the existing account, explicit complete domain list and cert-name. Do not blindly add --agree-tos to a command or register a new staging/production account. Existing staging-account capability was not inspected; if staging needs new account terms, reuse an approved staging account or gate that exact decision. Verify actual installed Certbot help/options before applying expansion. Reverify renewal config's four-name webroot map and dry-run renewal/deploy-hook behavior after installation. Never present a staging certificate publicly.

The existing hook may restart the shared affected Kong service on certificate promotion. This is not an unrelated workload restart, but it can briefly affect website/phone/admin routes: stage rollback and coordinate a safe cutover, do not interrupt an active call. No unrelated application service may be restarted. Do not claim zero downtime.

## 4. Concrete application contract for implementation

These are DESIGN DECISIONS for the child, not installed resources:

- Public origin: https://ashfall.teknetik.co (canonical configured value; do not construct redirects/CSRF origins from arbitrary request headers).
- Production upstream: http://127.0.0.1:3187. Bind EXACTLY 127.0.0.1, not 0.0.0.0 or LAN IP. Port 3187 is absent from live listening inventory; recheck immediately before starting. Local QA can use 127.0.0.1:3188 with isolated data and report its actual PID/port. Neither is reserved by this preflight.
- Host systemd packaging, not a new Docker network. Service name ashfall-promo.service, dedicated unprivileged system user ashfall-promo. Node app uses the host Node runtime; live /usr/bin/node version v26.7.0 and npm 11.19.0. Verify app dependencies/tests against that runtime and pin lockfile; do not install/change root game dependencies or globally upgrade Node.
- Built immutable releases: /srv/ashfall-promo/releases/<candidate-id>, selected by /srv/ashfall-promo/current. Root-owned code, app read-only access. Actual production entrypoint must be supplied by the app child, not guessed by ops. A host service should explicitly run that production entrypoint, not a dev server. These paths do not exist yet; install only on deployment card.
- Mutable persistent data: /var/lib/ashfall-promo/community.sqlite (including SQLite sidecar files), app-owner-only directory mode 0700, data files 0600. App must accept a database path and survive restart without clearing accounts/comments. No user data in git, public static tree, release directory or localStorage.
- Private config: /etc/ashfall-promo/app.env, root/service-only access, with non-public secrets if the implementation needs them. No default admin password. Moderation bootstrap is explicit private CLI or equivalent, not a public unauthenticated endpoint.
- Hardened unit: Restart=on-failure, UMask=0077, NoNewPrivileges=true, ProtectSystem=strict, ProtectHome=true and writable allowance only for persistent state. Verify actual runtime compatibility before claiming these settings work; do not hide native hash/SQLite module failures.
- Include health endpoint GET /api/health (non-sensitive status only), migration/init procedure, app-only production build/start, consistent SQLite backup/restore tooling and tests. Do not expose repo/content inventories/ops/evidence/node_modules/DB as static files.
- Backups: selected destination /backup/hdd/ashfall-promo, not scratch. Mounted /backup/hdd has about 1.5 TB free; directory does not exist yet. Create root/service-restricted backup directory on deployment, daily consistent SQLite backup (SQLite backup API, not live file-only copy), bounded retention e.g. seven daily plus four weekly, include migration/app identity. Protect credential hashes and sessions as sensitive data. Define/verify ownership and restore drill; any off-host copy requires approved encrypted custody. Existing backup inclusion for this new path was NOT verified; local same-host backup is not disaster recovery.

### Proxy trust and cookies

Kong is host-networked, so backend sees a loopback proxy. Trust ONLY loopback and this one controlled proxy; never trust all proxies/CIDRs or arbitrary X-Forwarded-* chain supplied by clients. For the Ashfall route, explicitly replace forwarded client-IP/proto/host inputs with authoritative values at Kong (socket client IP, https, ashfall.teknetik.co), and prove forged forwarding headers cannot affect auth/rate-limit/origin/redirect decisions. Verify the installed 3.13 PDK functions when authoring the route plugin. Do not add global trusted_ips changes that alter existing Cloudflare/phone routes. Direct Ashfall DNS means the socket peer normally is the client; if later enabling Cloudflare proxying, that changes the trust/abuse contract and needs separate review.

App cookies: Secure, HttpOnly, SameSite=Lax or stronger; host-only (no Domain=.teknetik.co), scoped Path=/, expiry bounded. HTTPS is a configured production property, not inferred from untrusted headers. CSRF/origin protections and rate limits are implemented server-side. QA can exercise secure sessions via a controlled local HTTPS harness; do not weaken production cookies to accommodate plain localhost HTTP.

## 5. Kong route contract and minimal mutation set

Add service ashfall-promo, protocol http, host 127.0.0.1, port 3187, connect_timeout 3000, read/write_timeout 15000, retries 0. Add route ashfall-promo-https, hosts [ashfall.teknetik.co], paths [/], protocols [https], strip_path false, preserve_host true, request/response buffering true unless an explicitly tested feature requires otherwise. Add bounded request-size-limiting compatible with app limits and the forwarding-header normalization described above. No global authentication plugin; public pages stay public and posting auth is the application responsibility.

Affected existing infrastructure files only:

1. /etc/kong-single-site/single-site.yaml — append the scoped service/route, preserve every existing entity.
2. /etc/kong-single-site/host-guard.conf — add Ashfall to both exact hostname lists, retain Host/SNI equality.
3. /etc/kong-single-site/http01-nginx.conf — add dedicated Ashfall server/challenge/HTTPS redirect block, retain current three-host behavior and default deny.
4. /usr/local/sbin/teknetik-deploy-certificate — update exact four-host validation and served checks, retain root control, lock, fingerprint checks and rollback.
5. Existing teknetik.co Certbot lineage and renewal metadata — approved-account expansion to all four names.
6. New app service/config/data/backup installation only on deployment card.

No default DNS, NAT, UFW, Kong image/plugin allowlist/Admin listener changes. No generic service/route API POST: Admin API is off and this is DB-less. No decK gateway sync or historical Kong token workflow. Validate a complete declarative candidate using the PINNED actual image in an isolated non-public environment before activation.

The declarative YAML and guard are SINGLE-FILE bind mounts. Atomic host replacement can leave an existing container pointing to the old inode. The deployment installer must deliberately handle this (e.g. recreate only the affected dedicated Kong container via its existing unit after validating the staged candidate); do not assume a host file write plus reload has updated a file mount. Read back host hashes AND container-visible content/hashes, then actual route responses. A restart/reload approach is a deployment operation, never an action on this preflight.

## 6. Snapshot and rollback contract

Before ANY writes, re-read all live inputs and compare baseline hashes below, candidate identity, security PASS and QA PASS. If unrelated concurrent drift appears, pause and reconcile; do not overwrite it. Snapshot into a timestamped root-only directory (planned /var/lib/ashfall-promo-deploy/<UTC>/, not yet created), with metadata-safe copies/report under promo-site/ops. Include affected config/units/drop-ins, current TLS symlink, previous TLS release and Certbot lineage/archive/renewal state, readiness markers, HTTP handler config, hook, gateway image/environment/listeners, app release pointer/state and exact Cloudflare record. Secrets/private keys stay in root-controlled snapshot, not repo/artifacts. Record UFW/NAT read-only baseline; no router/firewall change is planned.

Rollback must restore exact pre-change declarative YAML, guard, HTTP config, hook, TLS pointer and matching Certbot lineage/renewal state, then validate and reactivate ONLY affected ingress services. Do not leave a restored three-host hook paired with a four-host renewal lineage. Stop the new app or restore its prior release as appropriate; preserve users/comments created after publication and use only migration-compatible rollback. Do not overwrite a populated production DB with test fixtures or blindly restore an older backup. DNS rollback is unnecessary if unchanged; if a separately justified record mutation becomes needed, snapshot/readback/restore the exact record only.

After rollback verify trusted apex HTTPS 200, www redirect, phone route behavior without a real call/token, admin route continuity without credentials, no new management listeners and unknown Host/SNI denial. After success verify those same regressions plus trusted Ashfall chain/SAN, Ashfall HTTP redirect, full account/comment lifecycle and persistence through an APP-only restart. Genuine off-LAN tests must distinguish external vantage from LAN hairpin; this preflight's WAN curl checks are LAN-origin and are not independent off-LAN evidence.

Baseline SHA-256, collected live (recompute before apply):

| File | SHA-256 |
|---|---|
| /etc/kong-single-site/single-site.yaml | f14dd0d32afe81bc9930deb0ca22fcae0650b6a2b763712086b97a251acaa95d |
| /etc/kong-single-site/host-guard.conf | b15c63bbe986bfe45080bf2c17258e9c0df699694f8895e885e262f254c27c3f |
| /etc/kong-single-site/http01-nginx.conf | c14d3685a89a4cb518ee4c16df9ed33ad011f9521624b7dd69624c65ae3f6e98 |
| /usr/local/sbin/teknetik-deploy-certificate | 2ec9dc33bda6aee9530c748785d49b41aac1ff4c0080bd9fec6d1e93ac203af9 |
| /etc/systemd/system/kong-single-site.service | dbd1453a59b35b2ee17de99269446566fcec0452df6ed771633c083438bd0a88 |
| /etc/systemd/system/kong-single-site-http01.service | 32ec6cb25c2030f9d312f95c2ea9c4d62e69cb6b2b9b7aca1ace8b0118068bdd |
| /etc/systemd/system/kong-single-site-renew.service | ae576143e495c6148dc9bf0fd5d8107b928762e7341f361eac898ab54ea2c713 |
| /etc/systemd/system/kong-single-site-renew.timer | c250979c9b082815033bf2b70727bde752a7411902312ce1317a4418e0f899af |
| /etc/letsencrypt/renewal/teknetik.co.conf | 3e241da29f799b8c7794ed32b1a214a6232f5fc3061430257695b45286427de0 |

## 7. Actual checks and outstanding gates

Performed:

- Cloudflare authenticated exact zone/record/permission GETs; parent/authoritative/two recursive DNS checks.
- sudo capability and Docker permission diagnosis; container inspect/version; unit/timer/config/mount and listener inventory.
- Router read-only WAN/NAT and UFW inventory; selected backend port absent from listening inventory.
- Public certificate SAN/expiry from installed public certificate; renewal config/hook/last successful reconciliation inspection; original consent history retrieval.
- https://teknetik.co/ -> 200 with certificate verification successful from this LAN host.
- https://ashfall.teknetik.co/ -> curl TLS hostname validation failure (error 60), as expected from missing SAN.
- Loopback HTTPS with Ashfall Host/SNI, explicitly bypassing certificate trust for guard diagnosis ONLY -> 421. This is not a trusted HTTPS pass.
- http://ashfall.teknetik.co/ -> 421. Loopback challenge path with Host Ashfall -> 421; same nonexistent token with Host apex -> 404.

Not performed/NOT claimed: live infrastructure mutation, external write permission proof, new issuance, CA-side contact retrieval, four-host renewal/rollback dry run, off-LAN token fetch, production app installation, persistent backup restore, application QA/security, public signup/posting, Unity interaction. Installed certbot regr.json's empty body is specifically not proof of contact state. Those are deployment/review prerequisites, not reasons to hold the completed read-only preflight or implementation dependency.

Child implementer must consume this contract and provide the real executable entrypoint/env names, isolated local app, tests and candidate identity. Deployment child must consume the same contract and security/QA reports before any exposure. All descendants/comments/lookups use board=Ashfall.

## Official technical references (not live-host evidence)

- Kong DB-less declarative topology (opened and verified): https://developer.konghq.com/gateway/db-less-mode/
- Certbot authoritative documentation: https://eff-certbot.readthedocs.io/en/stable/using.html

These references support mechanism selection only. Installed 3.13 behavior, Certbot CLI and the actual narrow candidate must be exercised before deployment; latest documentation is not a substitute for installed-version verification.
