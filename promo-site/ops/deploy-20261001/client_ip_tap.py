#!/usr/bin/env python3
"""Passive loopback capture proving what Kong forwards to the app (deployment gate D1).

Run as root for a bounded time. Prints ONLY the request line and the X-Ashfall-Client-IP header of
requests to 127.0.0.1:3187 whose path contains the given probe token; cookies, bodies and other
headers are never printed or stored.

  sudo python3 client_ip_tap.py <probe-token> <seconds>
"""
import socket
import sys
import time

token, seconds = sys.argv[1].encode(), float(sys.argv[2])
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
s.bind(("lo", 0))
s.settimeout(0.5)
deadline = time.monotonic() + seconds
seen = set()
while time.monotonic() < deadline:
    try:
        frame = s.recv(65535)
    except TimeoutError:
        continue
    start = frame.find(b"GET /")
    if start < 0 or token not in frame[start:start + 300]:
        continue
    lines = frame[start:].split(b"\r\n")
    request = lines[0].decode("latin-1")
    ips = [ln.decode("latin-1") for ln in lines[1:] if ln.lower().startswith(b"x-ashfall-client-ip:")]
    key = (request, tuple(ips))
    if key not in seen:
        seen.add(key)
        print(f"{request}  |  {' ; '.join(ips) or 'NO X-Ashfall-Client-IP'}", flush=True)
