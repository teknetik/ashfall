"""Loopback-only Ward native developer UI. Python stdlib; no Unity assets are edited."""
import argparse
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import threading
import time
import uuid
from urllib.parse import urlsplit

from model import seed, validate, diagnostics
from npc_db import initialize as initialize_npcs, list_npcs
from ai_authoring import AuthoringJobs, AuthoringError

HERE = Path(__file__).resolve().parent
UNITY_CRAFT_EXPORT = HERE.parent.parent / 'AthenHill/Assets/AthenHill/Data/Crafting/Export/ward-crafting.v1.json'
BODY_MAX = 512 * 1024  # draft import; command has a separate 8 KiB cap
COMMANDS = {
    'dev.state': {}, 'dev.item.grant': {'itemId': str, 'quantity': int},
    'dev.item.remove': {'itemId': str, 'quantity': int},
    'dev.credits.grant': {'amount': int}, 'dev.credits.remove': {'amount': int},
    'dev.time.set': {'hour': (int, float)}, 'dev.time.pause': {'paused': bool},
    'dev.time.speed': {'speed': (int, float)}, 'dev.time.reset': {},
    'dev.encounter.activate': {'key': str}, 'dev.encounter.reset': {'key': str},
    'dev.range.raise': {}, 'dev.interaction.resetCityVisit': {},
}
ITEM_ID = re.compile(r'^[a-z][a-z0-9_]{1,63}$')


def safe_dir(path):
    home = Path.home().resolve()
    expanded = Path(path).expanduser()
    if '..' in expanded.parts: raise ValueError('Parent traversal is not allowed in directory paths')
    candidate = Path(os.path.abspath(expanded))
    if not candidate.is_relative_to(home): raise ValueError('QA directory must be under the current user home')
    cursor = candidate
    while cursor != home:
        if cursor.is_symlink(): raise ValueError('Symlink in QA directory path')
        cursor = cursor.parent
    candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
    return candidate


def safe_file(folder, name):
    path = folder / name
    if path.is_symlink(): raise ValueError('Symlinked bridge/draft files are not allowed')
    return path


@contextmanager
def draft_directory(path):
    """Pin each directory below home; never follow a swapped directory link."""
    home = Path.home().resolve()
    relative = path.parent.relative_to(home)
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def read_draft(path):
    with draft_directory(path) as folder:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Draft store must be a regular file')
            raw = stream.read(BODY_MAX + 1)
            if len(raw) > BODY_MAX: raise ValueError('Draft store exceeds size limit')
    return json.loads(raw)


def write_draft(path, raw):
    if len(raw) > BODY_MAX: raise ValueError('Draft store exceeds size limit')
    with draft_directory(path) as folder:
        tmp = '.' + path.name + '.' + secrets.token_hex(8) + '.tmp'
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush(); os.fsync(stream.fileno())
            try:
                target = os.stat(path.name, dir_fd=folder, follow_symlinks=False)
                if not stat.S_ISREG(target.st_mode): raise ValueError('Draft store must be a regular file')
            except FileNotFoundError:
                pass
            os.replace(tmp, path.name, src_dir_fd=folder, dst_dir_fd=folder)
            os.fsync(folder)
        finally:
            try: os.unlink(tmp, dir_fd=folder)
            except FileNotFoundError: pass


def draft_bytes(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')


def load_json(path, max_bytes=BODY_MAX):
    if not path.exists(): return None
    if path.stat().st_size > max_bytes: raise ValueError('File exceeds size limit')
    return json.loads(path.read_text(encoding='utf-8'))


class App(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port, qa, drafts, env_file=None):
        self.qa = safe_dir(qa)
        self.drafts = safe_dir(drafts)
        self.draft_file = safe_file(self.drafts, 'drafts.v1.json')
        self.npc_file = safe_file(self.drafts, 'npcs.sqlite3')
        initialize_npcs(self.npc_file)
        self.authoring = AuthoringJobs(HERE.parents[2], safe_dir(self.drafts / 'generated'), env_file)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        existing = read_draft(self.draft_file)
        if existing is None:
            existing = seed()
            write_draft(self.draft_file, draft_bytes(existing))
        errors = validate(existing)
        if errors: raise ValueError('Invalid draft store: ' + '; '.join(errors[:3]))
        super().__init__(('127.0.0.1', port), Handler)

    def status(self):
        path = safe_file(self.qa, 'dev-state.json')
        if not path.exists(): return {'status': 'absent', 'reason': 'No opted-in development player', 'state': None}
        try:
            age = max(0, time.time() - path.stat().st_mtime)
            data = load_json(path, 2 * 1024 * 1024)
            if not isinstance(data, dict) or data.get('schemaVersion') != 1 or data.get('source') != 'unity' or not isinstance(data.get('build'),dict) or data['build'].get('development') is not True or not isinstance(data.get('items'),list) or any(not isinstance(x,dict) or not isinstance(x.get('id'),str) for x in data['items']) or data.get('encounters') is not None and (not isinstance(data['encounters'],list) or any(not isinstance(e,dict) or not isinstance(e.get('key'),str) for e in data['encounters'])):
                return {'status': 'incompatible', 'reason': 'Invalid Unity development state/schema', 'state': None, 'ageSeconds': age}
            if not data.get('available'):
                return {'status': 'unavailable', 'reason': data.get('reason', 'No playable session'), 'state': None, 'ageSeconds': age}
            if age >= 2:
                return {'status': 'stale', 'reason': 'Unity sample is older than 2 seconds', 'state': None, 'ageSeconds': age, 'lastSampleUtc': data.get('utc')}
            return {'status': 'connected', 'state': data, 'ageSeconds': age}
        except (OSError, ValueError, json.JSONDecodeError, TypeError) as e:
            return {'status': 'incompatible', 'reason': str(e), 'state': None}

    def draft(self):
        data = read_draft(self.draft_file)
        if data is None: raise ValueError('Draft store missing')
        raw = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
        return data, hashlib.sha256(raw).hexdigest()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): print('%s %s' % (self.address_string(), format % args))
    def response(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(raw)
    def reject(self, status, message): self.response(status, {'error': message})
    def safe_request(self):
        host = self.headers.get('Host', '')
        port = self.server.server_port
        if host not in (f'127.0.0.1:{port}', f'localhost:{port}'): self.reject(403, 'Invalid Host'); return False
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            self.reject(403, 'Foreign Origin'); return False
        return True
    def body(self, limit):
        length = self.headers.get('Content-Length')
        if not length or len(length)>12 or not length.isascii() or not length.isdecimal(): self.reject(411, 'Content-Length required'); return None
        n = int(length)
        if n > limit: self.reject(413, 'Request too large'); return None
        try: return json.loads(self.rfile.read(n))
        except (ValueError, UnicodeError): self.reject(400, 'Malformed JSON'); return None
    def do_GET(self):
        if not self.safe_request(): return
        path = urlsplit(self.path).path
        if path == '/api/status': return self.response(200, self.server.status())
        if path == '/api/npcs':
            try: return self.response(200, {'source': 'npc-database', 'npcs': list_npcs(self.server.npc_file)})
            except (OSError, ValueError, sqlite3.DatabaseError): return self.reject(409, 'NPC database unavailable')
        if path == '/api/ai':
            return self.response(200, {'config': self.server.authoring.config(), 'jobs': self.server.authoring.list()})
        if path.startswith('/api/ai/assets/'):
            match = re.fullmatch(r'/api/ai/assets/([0-9a-f]{32})\.(png|wav|json)', path)
            if not match: return self.reject(404, 'Unknown generated asset')
            try: data = self.server.authoring.media(*match.groups())
            except (OSError, ValueError): return self.reject(404, 'Generated asset unavailable')
            mime = {'png': 'image/png', 'wav': 'audio/wav', 'json': 'application/json'}[match[2]]
            self.send_response(200); self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data))); self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if match[2] == 'json': self.send_header('Content-Disposition', 'attachment; filename="ashfall-' + match[1] + '.json"')
            self.end_headers(); self.wfile.write(data); return
        if path == '/api/unity-crafting':
            try:
                data = load_json(UNITY_CRAFT_EXPORT, 2 * 1024 * 1024)
                if not isinstance(data, dict) or data.get('schema') != 'ward-crafting/1': raise ValueError('Incompatible Unity Editor export')
                return self.response(200, {'source': 'unity-editor-export', 'data': data})
            except (OSError, ValueError, json.JSONDecodeError):
                return self.reject(409, 'Unity Editor export unavailable or incompatible')
        if path == '/api/config': return self.response(200, {'token': self.server.token, 'bridgeDir': str(self.server.qa)})
        if path == '/api/draft':
            try:
                data, rev = self.server.draft()
                return self.response(200, {'source': 'draft', 'revision': rev, 'data': data, 'diagnostics': diagnostics(data)})
            except (OSError, ValueError, json.JSONDecodeError) as e:
                return self.reject(409, 'Draft store unavailable: ' + type(e).__name__)
        static = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/authoring.js': ('authoring.js', 'text/javascript; charset=utf-8')}
        if path not in static: return self.reject(404, 'Not found')
        filename, mime = static[path]; data = (HERE / filename).read_bytes()
        self.send_response(200); self.send_header('Content-Type', mime); self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if not self.safe_request(): return
        if self.headers.get('X-Ward-CSRF') != self.server.token: return self.reject(403, 'Missing/invalid CSRF token')
        path = urlsplit(self.path).path
        if path not in ('/api/command','/api/draft','/api/import','/api/ai/generate','/api/ai/cancel'): return self.reject(404, 'Not found')
        body = self.body(8192 if path == '/api/command' else BODY_MAX)
        if body is None: return
        if path == '/api/command': return self.send_command(body)
        if path in ('/api/ai/generate', '/api/ai/cancel'):
            try:
                if path == '/api/ai/generate': job = self.server.authoring.start(body)
                else:
                    if not isinstance(body, dict) or set(body) != {'id'} or not isinstance(body['id'], str):
                        return self.reject(400, 'Expected request ID')
                    job = self.server.authoring.cancel(body['id'])
                return self.response(202 if path.endswith('generate') else 200, {'job': job})
            except AuthoringError as error: return self.reject(400, str(error))
            except OSError: return self.reject(409, 'Local authoring storage is unavailable. Check the draft directory.')
        with self.server.lock:
            if not isinstance(body, dict) or set(body) != {'revision','data'} or not isinstance(body['revision'],str): return self.reject(400, 'Expected revision and data')
            try: current, revision = self.server.draft()
            except (OSError, ValueError, json.JSONDecodeError) as e:
                return self.reject(409, 'Draft store unavailable: ' + type(e).__name__)
            if body['revision'] != revision: return self.reject(409, 'Draft changed; reload before saving')
            try: errors = validate(body['data'])
            except (TypeError, KeyError, ValueError, RecursionError) as e:
                return self.reject(400, 'Malformed draft document: ' + type(e).__name__)
            if errors: return self.response(400, {'errors': errors})
            try:
                raw = draft_bytes(body['data'])
                if len(raw) > BODY_MAX: return self.reject(413, 'Serialized draft exceeds size limit')
                report = diagnostics(body['data'])
            except (ValueError, TypeError, RecursionError, OverflowError) as e:
                return self.reject(400, 'Draft could not be prepared: ' + type(e).__name__)
            try: write_draft(self.server.draft_file, raw)
            except ValueError as e:
                return self.reject(409, 'Draft store unavailable: ' + type(e).__name__)
            except OSError as e:
                return self.reject(409, 'Draft store unavailable: ' + type(e).__name__)
            rev = hashlib.sha256(json.dumps(body['data'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            return self.response(200, {'source': 'draft', 'revision': rev, 'data': body['data'], 'diagnostics': report})
    def send_command(self, body):
        if not isinstance(body,dict) or body.get('action') not in COMMANDS: return self.reject(400, 'Unknown command')
        action = body['action']; fields = COMMANDS[action]
        if set(body) != set(fields) | {'action'} or any(type(body[k]) not in (typ if isinstance(typ,tuple) else (typ,)) for k,typ in fields.items()): return self.reject(400, 'Invalid command arguments')
        if 'quantity' in body and not 1 <= body['quantity'] <= 99 or 'amount' in body and not 1 <= body['amount'] <= 10000:
            return self.reject(400, 'Out of range')
        if 'hour' in body and (not math.isfinite(body['hour']) or not 0 <= body['hour'] < 24) or 'speed' in body and (not math.isfinite(body['speed']) or not .1 <= body['speed'] <= 120):
            return self.reject(400, 'Out of range')
        if 'itemId' in body and (not ITEM_ID.fullmatch(body['itemId']) or len(body['itemId']) > 64): return self.reject(400, 'Invalid item ID')
        if not self.server.lock.acquire(blocking=False): return self.reject(409, 'Another operation is in progress')
        try:
            status = self.server.status()
            if status['status'] != 'connected': return self.reject(503, status['reason'] if 'reason' in status else 'No live player')
            state = status['state']
            if 'itemId' in body and body['itemId'] not in {x['id'] for x in state['items']}:
                return self.reject(400, 'Item is not in live Unity catalogue')
            if 'key' in body and (not isinstance(body['key'],str) or body['key'] not in {e['key'] for e in state.get('encounters') or []}):
                return self.reject(400, 'Unknown authored encounter')
            command_path = safe_file(self.server.qa,'command.json')
            if command_path.exists(): return self.reject(409, 'QA command slot occupied by another client')
            command = dict(body, id=uuid.uuid4().hex)
            # The NativeQa client is single-slot. Never overwrite its command or stale ACK.
            tmp = safe_file(self.server.qa, 'command.tmp')
            try:
                with tmp.open('x', encoding='utf-8') as f: json.dump(command, f)
                os.link(tmp, command_path)  # exclusive creation; no rename-overwrite race
                tmp.unlink()
            except FileExistsError: return self.reject(409, 'QA command slot occupied')
            finally:
                if tmp.exists() and not tmp.is_symlink(): tmp.unlink()
            deadline = time.monotonic() + 10
            ack_path = safe_file(self.server.qa,'ack.json')
            while time.monotonic() < deadline:
                try:
                    ack = load_json(ack_path, 8192)
                    if isinstance(ack,dict) and ack.get('id') == command['id']:
                        # Always re-read after ACK; do not synthesize success values.
                        return self.response(200 if ack.get('success') is True else 422, {'ack': ack, 'status': self.server.status()})
                except (OSError, ValueError, json.JSONDecodeError): pass
                time.sleep(.025)
            # Delete only the exact command we wrote, not a newer client's command.
            try:
                if load_json(command_path,8192) == command: command_path.unlink()
            except (OSError,ValueError,json.JSONDecodeError): pass
            return self.response(504, {'error': 'Command not confirmed; effect unknown until a new Unity snapshot', 'status': self.server.status()})
        finally: self.server.lock.release()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--qa-dir', required=True, help='Exact --athen-qa directory (under home)')
    p.add_argument('--draft-dir', default=str(HERE / 'data'), help='Local draft store directory (under home)')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--env-file', help='Optional local .env path; otherwise discover repository/worktree root .env')
    args=p.parse_args()
    if not 1 <= args.port <= 65535: p.error('Port must be 1..65535')
    server=App(args.port,args.qa_dir,args.draft_dir,args.env_file)
    print(f'Ward dev UI: http://127.0.0.1:{server.server_port}/ ; QA dir: {server.qa}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == '__main__': main()
