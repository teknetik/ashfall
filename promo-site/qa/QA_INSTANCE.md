# Ashfall promo: isolated local QA instance

Started 2026-10-01 14:37 BST by designer (task t_96803b8f, run 127). **Not public, not production.**

| Item | Value |
| --- | --- |
| Candidate release | `20261001-77c53f7228e8` |
| Tarball | `app/release/ashfall-promo-20261001-77c53f7228e8.tar.gz`, sha256 `84509348e68b40d2f63fc1dd75f01015a10d9d7b327696bf14c59f4f4a291496` |
| Full hash manifest | `app/release/MANIFEST.json`, `app/release/SHA256SUMS` (source, inputs, dist, tarball) |
| Running code | `qa/ashfall-promo-20261001-77c53f7228e8/` (unpacked from the tarball after `sha256sum -c`; read-only) |
| Process | user systemd transient unit `ashfall-promo-qa.service`, **MainPID 884219**, `/usr/bin/node` v26.8.1 |
| Listen | **https://127.0.0.1:3188** (loopback only), self-signed cert for `ashfall.teknetik.co`, valid until 31 Oct 2026, SHA-256 fingerprint `1D:60:13:69:0C:B6:60:F5:A3:09:90:35:CC:F9:7C:B6:27:C0:C4:26:83:0F:2E:63:51:4F:A0:6A:5D:35:40:F5` |
| Data | `qa/data/community.sqlite`, isolated and clean at start (0 users and 0 posts, schema v1). No real user data. |
| Cookies | production policy unchanged (`__Host-ashfall_session`, Secure, HttpOnly, SameSite=Lax) |
| Accounts | none pre-created; no default admin. Create test accounts in the UI. To test moderation, grant the role to an account you created: `cd qa/ashfall-promo-20261001-77c53f7228e8 && ASHFALL_PUBLIC_ORIGIN=https://ashfall.teknetik.co ASHFALL_DB_PATH=../data/community.sqlite /usr/bin/node server/cli.mjs grant-moderator <username>` |

## Access

```sh
curl -k -H 'Host: ashfall.teknetik.co' https://127.0.0.1:3188/api/health
chromium --host-resolver-rules="MAP ashfall.teknetik.co:443 127.0.0.1:3188" --ignore-certificate-errors https://ashfall.teknetik.co/
# Playwright suite against this instance (creates random throwaway accounts/posts here):
cd app && E2E_PORT=3188 node scripts/e2e.mjs
```

## Control

```sh
systemctl --user status ashfall-promo-qa
journalctl --user -u ashfall-promo-qa -f
systemctl --user stop ashfall-promo-qa      # the transient unit then disappears; restart with the systemd-run line below
```

The unit was started with:

```sh
systemd-run --user --unit=ashfall-promo-qa -E PATH=/usr/bin:/bin -p NoNewPrivileges=true -p ProtectSystem=strict \
  -p ProtectHome=read-only -p ReadWritePaths=$PWD/qa/data -p PrivateTmp=true -p RestrictNamespaces=true -p LockPersonality=true \
  -p RestrictRealtime=true -p "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX" -p SystemCallArchitectures=native \
  -p SystemCallFilter=@system-service -p "SystemCallFilter=~@privileged @resources" -p UMask=0077 -p Restart=on-failure \
  --working-directory=$PWD/qa/ashfall-promo-20261001-77c53f7228e8 \
  $PWD/qa/ashfall-promo-20261001-77c53f7228e8/deploy/run-qa.sh $PWD/qa/data 3188
```

## Evidence for this candidate

- `app/evidence/check-*.log`: full `npm run check` (exit 0). Build OK; lint and typecheck clean; tests 28/28; E2E 14/14 against a temp server.
- `app/evidence/e2e/20261001T133556Z/`: E2E screenshots + report.json (temp server).
- `app/evidence/e2e/20261001T133636Z/`: the same 14/14 run against this packaged QA instance, before its DB was reset to clean.
