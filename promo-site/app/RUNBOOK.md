# Ashfall promo site: operations runbook

This runbook covers install, release, migrations, backups, restore, moderation and rollback. The infrastructure contract (port, paths, user, Kong route, TLS) is in [../ops/PREFLIGHT.md](../ops/PREFLIGHT.md) §4–6. **Nothing in this file has been executed against production.** Installation, ingress and TLS changes belong to the deployment card, after independent security and QA review.

## Fixed contract

| Item | Value |
| --- | --- |
| Service | `ashfall-promo.service`, system user/group `ashfall-promo` (no login shell, no home) |
| Bind | `127.0.0.1:3187` exactly (the app refuses to bind non-loopback) |
| Public origin | `https://ashfall.teknetik.co` (TLS terminated by Kong; app cookies are always `Secure`) |
| Releases | `/srv/ashfall-promo/releases/<release-id>/` (root-owned, read-only to the service), with symlink `/srv/ashfall-promo/current` |
| Config | `/etc/ashfall-promo/app.env` (root:ashfall-promo 0640), from `deploy/app.env.example` |
| Data | `/var/lib/ashfall-promo/community.sqlite` (+ `-wal`/`-shm`), dir 0700 via systemd `StateDirectory` |
| Backups | `/backup/hdd/ashfall-promo/` (ashfall-promo 0700), daily 03:17 ± 10 min, 7 daily + 4 weekly |
| Health | `GET /api/health` returns 200 `{"status":"ok","db":"ok","schema":N,"release":"<id>","uptimeS":N}`, or 503 when the DB is unreadable. It is accepted with `Host: ashfall.teknetik.co` or a loopback Host (`127.0.0.1[:port]`, `localhost`) for local monitoring; every other path returns 421 for any non-canonical Host. |
| Node | host `/usr/bin/node` (PREFLIGHT recorded v26.7.0; it read **v26.8.1** on 1 Oct 2026 14:35 BST, which the QA instance runs). Nothing is installed globally. |

Run every CLI command as the service user with the service environment. Use this fixed-path helper from an authorised administrator shell (systemd >= 254):

```sh
ash() {
  sudo /usr/bin/systemd-run --system --quiet --wait --pipe --collect \
    --expand-environment=no --service-type=exec \
    --uid=ashfall-promo --gid=ashfall-promo \
    --property=EnvironmentFile=/etc/ashfall-promo/app.env \
    --property=WorkingDirectory=/srv/ashfall-promo/current \
    --property=UMask=0077 --property=NoNewPrivileges=yes \
    --property=MemoryMax=512M --property=MemorySwapMax=64M \
    /usr/bin/node /srv/ashfall-promo/current/server/cli.mjs "$@"
}
```

The root system manager reads the root-controlled EnvironmentFile and starts only the fixed CLI as the service user; the shell passes the file path, never its contents. Values containing spaces, dollar signs or shell metacharacters follow systemd EnvironmentFile quoting, not shell evaluation. Environment expansion in command arguments is explicitly disabled. Do not source the file, use shell substitution, `eval`, `env KEY=value`, `--setenv` with secret values, or copy it into temporary files. Never pass passwords or invite codes as CLI arguments.

Keep the config directory and release tree root-owned and not service-writable (§2); no configurable executable or env-file path is accepted by this helper. This is an administrator convenience, NOT a restricted privilege boundary: do not grant untrusted users blanket sudo access to systemd-run or add a wildcard sudoers rule for it. Existing administrator sudo authorisation remains required. Each invocation uses a separate transient system service and does not restart the web service. `--wait` propagates CLI failure, `--pipe` returns its output, and `--collect` unloads the transient unit. The CLI never prints password hashes, session tokens, invite codes or post text. Environment variables remain accessible to root/the same service identity; this prevents argv leakage, not host compromise.

## 1. Build a release candidate (build host, inside `promo-site/app`)

```sh
npm ci
npm run check        # build, lint, typecheck, unit+integration, Playwright E2E — all must pass
npm run manifest     # writes dist/RELEASE, release/MANIFEST.json, release/SHA256SUMS, release/ashfall-promo-<id>.tar.gz
```

Record the `releaseId` and the tarball's SHA-256 from `release/MANIFEST.json` in the deployment card.

## 2. First install (deployment card only)

```sh
sudo useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin ashfall-promo
sudo install -d -o root -g root -m 0755 /srv/ashfall-promo /srv/ashfall-promo/releases
sudo install -d -o root -g ashfall-promo -m 0750 /etc/ashfall-promo
sudo install -d -o ashfall-promo -g ashfall-promo -m 0700 /backup/hdd/ashfall-promo
# Unpack and verify the candidate (replace <id>):
sha256sum -c ashfall-promo-<id>.tar.gz.sha256
sudo tar -xzf ashfall-promo-<id>.tar.gz -C /srv/ashfall-promo/releases --no-same-owner
sudo mv /srv/ashfall-promo/releases/ashfall-promo-<id> /srv/ashfall-promo/releases/<id>
sudo chown -R root:root /srv/ashfall-promo/releases/<id> && sudo chmod -R go-w,o+rX /srv/ashfall-promo/releases/<id>
sudo ln -sfn /srv/ashfall-promo/releases/<id> /srv/ashfall-promo/current
sudo install -o root -g ashfall-promo -m 0640 /srv/ashfall-promo/current/deploy/app.env.example /etc/ashfall-promo/app.env
sudoedit /etc/ashfall-promo/app.env      # review; optionally set an invite code generated on the host
sudo install -m 0644 /srv/ashfall-promo/current/deploy/ashfall-promo{.service,-backup.service,-backup.timer} /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/ashfall-promo.service
sudo ss -ltnp | grep -q ':3187 ' && echo 'PORT 3187 IN USE - stop' || true
sudo systemctl daemon-reload
sudo systemctl enable --now ashfall-promo.service ashfall-promo-backup.timer
curl -fsS -H 'Host: ashfall.teknetik.co' http://127.0.0.1:3187/api/health
sudo systemd-analyze security ashfall-promo.service | tail -1
```

`ExecStartPre` runs `cli.mjs migrate`, which creates the DB at schema v1 on first start. The hardening flags in the unit were exercised with Node 26 + `node:sqlite` + scrypt in a transient `systemd-run` sandbox, but **not** as the real system unit. Verify it on the host. Do not add `MemoryDenyWriteExecute=yes`, because the V8 JIT needs it off.

Then grant the first moderator to an account that already exists. There is no default admin account.

```sh
ash grant-moderator <username>
```

## 3. Upgrade / new release

1. Take a backup and confirm it verifies: `ash backup /backup/hdd/ashfall-promo` (this also prunes old backups), then `ash verify <file>`.
2. Unpack the new release beside the old one (step 2 commands), then `ln -sfn` `current` to it.
3. `sudo systemctl restart ashfall-promo` (ExecStartPre applies any pending migrations), then check `/api/health` for the new `release` id.
4. Smoke test: `/`, `/gallery`, `/discuss/world`, sign in, open the composer.

Migrations are forward-only and additive. The app refuses to open a DB whose schema is newer than the app (`newer DB refused` in the tests).

## 4. Rollback

- **App only, same schema:** `ln -sfn /srv/ashfall-promo/releases/<previous-id> /srv/ashfall-promo/current && systemctl restart ashfall-promo`. User data is untouched.
- **After a schema bump:** an older release will refuse the newer DB, so do **not** restore an older backup blindly. That would destroy posts and accounts created since. Prefer rolling forward with a fix. If rolling back is unavoidable, stop the service, take a fresh backup, then restore the pre-upgrade backup (§5). Record that the newer data is set aside in the `pre-restore` copy.
- **Ingress/TLS rollback** is defined in PREFLIGHT §6. It is independent of the app.

## 5. Backup, verify, restore

```sh
sudo systemctl start ashfall-promo-backup.service       # on demand; the timer runs it daily
ls -l /backup/hdd/ashfall-promo                          # community-<UTC>.sqlite + .json metadata (schema, counts, release)
ash verify /backup/hdd/ashfall-promo/community-<UTC>.sqlite

# Restore (service MUST be stopped; the current DB is first copied aside as community.sqlite.pre-restore-<UTC>):
sudo systemctl stop ashfall-promo
ash restore /backup/hdd/ashfall-promo/community-<UTC>.sqlite --yes
sudo systemctl start ashfall-promo
```

Backups use the SQLite online backup API, not a live file copy, and are `integrity_check`ed before they are kept. Files are 0600.

Backups contain password hashes and session hashes, so treat them as sensitive. They are same-host only: this is **not** disaster recovery. Any off-host copy needs separately approved encrypted custody.

The restore drill (backup, write, stop, restore, compare) runs in `npm test`. Run it again on the production host before going public.

## 6. Moderation

- In the web UI, a moderator gets a link to the moderation queue (`/moderation`) on their account page, plus moderator controls on each topic. Moderators can review reports, remove or restore posts (with a reason; the original text stays visible to moderators), lock or unlock topics and suspend accounts. Every action is written to `mod_log`.
- From the CLI: `ash suspend <username>`, `ash unsuspend <username>`, `ash revoke-moderator <username>`.
- Users can edit or delete their own posts, and delete their account (`/account`). Account deletion erases the username, password hash, sessions, likes and reports, and blanks the text of their posts. Replies under those posts are kept.
- Session cleanup: expired sessions are pruned hourly by the app; `ash prune-sessions` does it on demand.

## 7. Abuse controls and tuning

| Limit | Default | Where |
| --- | --- | --- |
| Requests per IP | 600 / min | `server/security.mjs` `LIMITS` |
| POSTs per IP | 120 / min | same |
| Signups per IP | `ASHFALL_SIGNUP_PER_IP_HOUR` (10) / h; 40 / h global | env + `LIMITS` |
| Logins | 20 / 15 min per IP; 8 failures / 15 min per account | `LIMITS` |
| Posts | 8 / 10 min, 60 / day per user | `LIMITS` |
| Body | 16 KB form; posts 10–2000 chars, replies 2–2000 | `server/app.mjs`, `server/store.mjs` |

To close signup quickly, set `ASHFALL_SIGNUP_ENABLED=false` (or set `ASHFALL_SIGNUP_INVITE_CODE`) and run `systemctl restart ashfall-promo`.

Kong should also enforce a request-size limit no larger than 16 KB for this route (PREFLIGHT §5).

The client IP header: by default the app limits on the socket peer. Behind host-network Kong that peer is 127.0.0.1, so **per-IP limits become global** until Kong overwrites a header (e.g. `X-Ashfall-Client-IP`) with the real socket client address. Once it does, set `ASHFALL_CLIENT_IP_HEADER=x-ashfall-client-ip`. The app ignores that header from non-loopback peers and accepts only a single valid IP.

## 8. Local QA instance (no infrastructure)

```sh
deploy/run-qa.sh /path/to/isolated-data 3188    # migrate + serve HTTPS with a throwaway self-signed cert
curl -k -H 'Host: ashfall.teknetik.co' https://127.0.0.1:3188/api/health   # Host must be the bare canonical host (no :port), else 421
chromium --host-resolver-rules="MAP ashfall.teknetik.co:443 127.0.0.1:3188" --ignore-certificate-errors https://ashfall.teknetik.co/
```

This is the production code path and cookie policy; only TLS is local. Create test accounts through the UI. Do not reuse real passwords.

## 9. Logs and troubleshooting

- `journalctl -u ashfall-promo -f`: one line per request (method, path without query, status, time). No cookies, bodies or IPs are logged.
- A 421 means the `Host` header is not `ashfall.teknetik.co`; check that Kong has `preserve_host: true`.
- A 403 "request origin" on a POST means `Origin` does not match `ASHFALL_PUBLIC_ORIGIN`. The proxy must not rewrite `Origin`.
- If the app exits at startup, the config was refused (the message names the variable) or `dist/content.json` is missing (an unbuilt release).
