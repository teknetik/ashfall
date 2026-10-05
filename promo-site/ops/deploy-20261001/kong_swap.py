#!/usr/bin/env python3
"""Install the Ashfall Kong route and host guard, with snapshot, probes and automatic rollback.

Shows the plan by default; pass --apply to change the live gateway. Run as yourself; it uses sudo
only for root steps. Modelled on teknetik-ai/deploy/go-live.py (step "kong").

Preconditions: the served certificate already covers ashfall.teknetik.co (the Ashfall probes verify
TLS for that name) and ashfall-promo.service answers on 127.0.0.1:3187.

  python3 kong_swap.py            # check drift, parse the candidate in the pinned image, change nothing
  python3 kong_swap.py --apply    # snapshot, install, restart Kong between phone calls, probe, roll back on failure
"""

from __future__ import annotations

import argparse
import hashlib
import re
import socket
import ssl
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = {"single-site.yaml": Path("/etc/kong-single-site/single-site.yaml"),
        "host-guard.conf": Path("/etc/kong-single-site/host-guard.conf")}
# Live hashes recorded in baseline/ on 1 Oct 2026 22:5x BST. Anything else means someone changed Kong since.
BASELINE = {"single-site.yaml": "e3b868350d0e5fa60e64aee02d1e0dc150145e0b692ee821401ab9ab44d4064d",
            "host-guard.conf": "b15c63bbe986bfe45080bf2c17258e9c0df699694f8895e885e262f254c27c3f"}
UNIT = "kong-single-site.service"
SNAPSHOTS = Path("/var/lib/ashfall-promo-deploy")
PHONE_PORT = 18744


def say(msg: str = "") -> None:
    print(msg, flush=True)


def run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=True, timeout=600)


def sudo(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return run("sudo", "-n", *cmd, check=check)


def sha_live(path: Path) -> str:
    return sudo("sha256sum", str(path)).stdout.split()[0]


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gateway(host: str, path: str = "/", verify: bool = True) -> tuple[int, bytes]:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection(("127.0.0.1", 8443), timeout=5) as raw, ctx.wrap_socket(raw, server_hostname=host) as tls:
        tls.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
        data = b""
        while chunk := tls.recv(65536):
            data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    return int(head.split(b" ", 2)[1]), body


PROBES = [  # host, path, status, needle, verify TLS
    ("teknetik.co", "/", 200, None, True),
    ("www.teknetik.co", "/", 308, None, True),
    ("phone.teknetik.co", "/", 404, None, True),
    # go-live.py's "Open your customer desk" was removed from the page in teknetik-ai 388a94a.
    ("teknetik.co", "/admin", 200, b"Customer desk", True),
    ("teknetik.co", "/admin/api/summary", 401, None, True),
    ("teknetik.co", "/administrator", 404, None, True),
    ("ashfall.teknetik.co", "/", 200, b"Ashfall", True),
    ("ashfall.teknetik.co", "/development", 200, b"timeline__item", True),
    ("ashfall.teknetik.co", "/api/health", 200, b'"status":"ok"', True),
    ("unknown.teknetik.co", "/", 421, None, False),
]


def probes() -> list[str]:
    failures = []
    for host, path, status, needle, verify in PROBES:
        try:
            got, body = gateway(host, path, verify)
        except (OSError, ssl.SSLError, ValueError, IndexError) as exc:
            failures.append(f"{host}{path}: {type(exc).__name__}: {exc}")
            continue
        if got != status or (needle and needle not in body):
            failures.append(f"{host}{path}: got {got}, expected {status}")
    return failures


def wait_for(what: str, check, seconds: int = 90) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except Exception:  # noqa: BLE001 - poll until the deadline
            pass
        time.sleep(1)
    raise RuntimeError(f"{what} did not come up within {seconds}s")


def quiet_phone(limit: int = 900) -> None:
    deadline = time.monotonic() + limit
    while True:
        out = run("ss", "-Htn", "state", "established", f"( sport = :{PHONE_PORT} )", check=False).stdout
        calls = len([line for line in out.splitlines() if line.strip()])
        if not calls:
            return
        if time.monotonic() > deadline:
            raise RuntimeError("a phone call has been running for 15 minutes; try later")
        say(f"  waiting for {calls} phone call(s) to finish before restarting Kong…")
        time.sleep(5)


def container_hashes() -> dict[str, str]:
    out = sudo("docker", "exec", "kong-single-site", "sha256sum", "/opt/kong/single-site.yaml", "/opt/kong/host-guard.conf").stdout
    return {Path(p).name: h for h, p in (line.split() for line in out.splitlines())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    cand = {name: HERE / "candidate" / name for name in LIVE}
    for name, path in LIVE.items():
        live = sha_live(path)
        if live == sha_file(cand[name]):
            say(f"  {name}: candidate already installed")
        elif live != BASELINE[name]:
            say(f"STOPPED: {path} changed since the baseline (sha256 {live[:12]}…); reconcile first")
            return 1
    unit = run("systemctl", "cat", UNIT).stdout
    images = set(re.findall(r"\bsha256:[0-9a-f]{64}\b", unit))
    if len(images) != 1:
        say("STOPPED: couldn't find the pinned Kong image")
        return 1
    image = images.pop()
    parsed = sudo("docker", "run", "--rm", "--network", "none", "--read-only", "--group-add=0", "--cap-drop", "ALL",
                  "--security-opt", "no-new-privileges", "--cpus=1", "--memory=768m", "--pids-limit=128",
                  "--tmpfs", "/tmp:rw,nosuid,size=128m",
                  "--mount", f"type=bind,src={cand['single-site.yaml']},dst=/opt/kong/single-site.yaml,readonly",
                  "--env=KONG_DATABASE=off", "--env=KONG_PLUGINS=pre-function,request-size-limiting",
                  "--env=KONG_UNTRUSTED_LUA=sandbox", "--env=KONG_PREFIX=/tmp/kong", "--env=KONG_ANONYMOUS_REPORTS=off",
                  "--entrypoint=/usr/local/bin/kong", image, "config", "parse", "/opt/kong/single-site.yaml", check=False)
    if parsed.returncode:
        say("STOPPED: Kong rejected the candidate:\n" + (parsed.stdout + parsed.stderr)[-1500:])
        return 1
    say("  candidate parses in a sandboxed Kong (same image as live)")
    if not args.apply:
        say("  would snapshot both files, install them, restart Kong between phone calls and probe every site")
        return 0

    snap = SNAPSHOTS / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    sudo("install", "-d", "-m", "700", "-o", "root", "-g", "root", str(SNAPSHOTS), str(snap))
    for name, path in LIVE.items():
        sudo("cp", "-p", str(path), str(snap / name))
    say(f"  snapshot: {snap}")
    quiet_phone()
    for name, path in LIVE.items():
        sudo("install", "-m", "640", "-o", "root", "-g", "root", str(cand[name]), str(path))
    sudo("systemctl", "restart", UNIT)
    try:
        wait_for("Kong", lambda: gateway("teknetik.co")[0] == 200)
        seen = container_hashes()
        for name in LIVE:
            if seen.get(name) != sha_file(cand[name]):
                raise RuntimeError(f"container sees a stale {name}")
        failures = probes()
        if failures:
            raise RuntimeError("; ".join(failures))
    except RuntimeError as problem:
        say(f"  FAILED ({problem}); restoring the snapshot")
        for name, path in LIVE.items():
            sudo("install", "-m", "640", "-o", "root", "-g", "root", str(snap / name), str(path))
        sudo("systemctl", "restart", UNIT)
        wait_for("Kong (restored)", lambda: gateway("teknetik.co")[0] == 200)
        say("  restored; teknetik.co answers again")
        return 1
    say("  installed; container sees the new files; all probes pass:")
    for host, path, status, *_ in PROBES:
        say(f"    {status}  {host}{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
