#!/usr/bin/env python3
"""NPC life pass (19 Nov 2026): ElevenLabs takes for Tamsin's dialogue, Ossa's arms-locker and range nodes, and the
barks in barks.json.

Run from the repository root:
  python3 art/showcase_20261119/npc_life/generate_voices.py            # dry run: what is cached, what would be spent
  python3 art/showcase_20261119/npc_life/generate_voices.py --generate [--budget 10000]
  python3 art/showcase_20261119/npc_life/generate_voices.py --master   # re-master cached takes into WAVs, no API calls

Same model, voice settings, request records and mastering as unity/tools/generate_npc_voices.py, so a dialogue take
written here is also accepted by that tool. Dialogue takes keep the canonical NpcVoices/<npc>-<node>.wav paths that
NpcVoiceAudit expects (an Ossa take that is replaced is moved to staging/.../previous_20261119/ first). Barks go to
Audio/ElevenLabs/NpcBarks/<speaker>-<line>.wav. No .meta files and no asset references are written here: Unity imports
the WAVs and the Editor installer (NpcLifeInstall20261119) binds them by asset path.

Spending stops at the budget, at the first refused request, or when the subscription has fewer characters left than
the next line. The API key is read from the project .env and never printed or written.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "barks.json").read_text())
MODEL = DATA["model_id"]
SETTINGS = DATA["voice_settings"]
OUTPUT = "mp3_44100_128"
ASSETS = ROOT / "unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs"
STAGE_DIALOGUE = ROOT / "unity/staging/elevenlabs-audio/npc-voices"
STAGE_BARKS = ROOT / "unity/staging/elevenlabs-audio/npc-barks-20261119"
PREVIOUS = STAGE_DIALOGUE / "previous_20261119"
API = "https://api.elevenlabs.io/v1"


def credential():
    content = (ROOT / ".env").read_text()
    match = re.search(r"^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.+)$", content, re.M)
    if not match:
        raise SystemExit("ELEVENLABS_API_KEY is absent from the project .env")
    return match.group(1).strip().strip("\"'")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subscription(key):
    req = urllib.request.Request(API + "/user/subscription", headers={"xi-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        s = json.load(r)
    return {k: s.get(k) for k in ("tier", "character_count", "character_limit", "next_character_count_reset_unix", "status")}


def jobs():
    """Every take in priority order: (a) Tamsin's dialogue, (b) Ossa's locker and range, (c) talking NPC barks, (d) walkers."""
    voices = {s["id"]: s["voice"] for s in DATA["speakers"]}
    out = []
    for d in DATA["dialogue"]:
        name = f"{d['npc']}-{d['node']}"
        out.append(dict(kind="dialogue", priority="a" if d["npc"] == "npc_tamsin" else "b", speaker=d["npc"], line=d["node"],
                        text=d["text"], voice=voices[d["npc"]], mp3=STAGE_DIALOGUE / f"{name}.mp3", record=STAGE_DIALOGUE / f"{name}.json",
                        wav=ASSETS / "NpcVoices" / f"{name}.wav"))
    for s in DATA["speakers"]:
        for line in s["lines"]:
            name = f"{s['id']}-{line['id']}"
            out.append(dict(kind="bark", priority="c" if s["kind"] == "npc" else "d", speaker=s["id"], line=line["id"],
                            text=line["text"], voice=s["voice"], mp3=STAGE_BARKS / f"{name}.mp3", record=STAGE_BARKS / f"{name}.json",
                            wav=ASSETS / "NpcBarks" / f"{name}.wav", trigger=line["trigger"]))
    return sorted(out, key=lambda j: j["priority"])  # stable: authored order inside a priority


def expected(job):
    body = {"text": job["text"], "model_id": MODEL, "voice_settings": SETTINGS}
    return {"voice_id": job["voice"]["id"], "model_id": MODEL, "output_format": OUTPUT, "request": body}


def cached(job):
    """True when a take for exactly this text/voice/model is on disk. A take for other text is moved aside (dialogue) or
    reported (barks), never reused."""
    mp3, record = job["mp3"], job["record"]
    if not mp3.exists():
        return False
    old = json.loads(record.read_text()) if record.exists() else {}
    if all(old.get(k) == v for k, v in expected(job).items()) and old.get("sha256") == sha(mp3):
        return True
    return None  # stale


def retire(job):
    PREVIOUS.mkdir(parents=True, exist_ok=True)
    for p in (job["mp3"], job["record"], job["wav"]):
        if p.exists():
            shutil.copy2(p, PREVIOUS / p.name)
    for p in (job["mp3"], job["record"]):
        if p.exists():
            p.unlink()


def request(job, key):
    voice_id = job["voice"]["id"]
    body = expected(job)["request"]
    url = f"{API}/text-to-speech/{voice_id}?output_format={OUTPUT}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as response:
        audio = response.read()
        headers = {k: response.headers[k] for k in ("request-id", "history-item-id", "character-cost") if k in response.headers}
        content_type = response.headers.get("Content-Type", "")
    if len(audio) < 1000 or "audio" not in content_type:
        raise RuntimeError("ElevenLabs did not return an audio file")
    job["mp3"].parent.mkdir(parents=True, exist_ok=True)
    tmp = job["mp3"].with_suffix(".tmp.mp3")
    tmp.write_bytes(audio)
    subprocess.run(["ffprobe", "-v", "error", str(tmp)], check=True)
    tmp.replace(job["mp3"])
    entry = {**expected(job), "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "response": headers, "sha256": sha(job["mp3"])}
    job["record"].write_text(json.dumps(entry, indent=2) + "\n")
    return int(headers.get("character-cost") or len(job["text"]))


def master(job):
    src, dst = job["mp3"], job["wav"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime and job["kind"] == "bark":
        return
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                    "-af", "loudnorm=I=-20:TP=-2:LRA=7", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(dst)], check=True)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], text=True)
    return round(float(out.strip()), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true", help="call the paid API for missing takes")
    ap.add_argument("--master", action="store_true", help="(re)master cached takes only")
    ap.add_argument("--budget", type=int, default=10000, help="characters this run may spend (default 10000)")
    args = ap.parse_args()
    key = credential() if args.generate else None
    before = subscription(key) if key else None
    if before:
        print(f"subscription before: {before['character_count']}/{before['character_limit']} used ({before['character_limit'] - before['character_count']} left)")
    spent, stopped, rows = 0, None, []
    for job in jobs():
        state = cached(job)
        if state is None and job["kind"] == "dialogue":
            # The old take spoke other text (Ossa's pre-hotbar key numbers): set aside before a new one is made.
            if args.generate and not stopped:
                retire(job)
            state = False
        if state is None:
            stopped = stopped or f"stale cached bark {job['mp3'].name}: delete it to regenerate"
        elif not state and args.generate and not stopped:
            left = before["character_limit"] - before["character_count"] - spent
            if spent + len(job["text"]) > args.budget:
                stopped = f"budget reached ({spent} of {args.budget})"
            elif len(job["text"]) > left:
                stopped = f"subscription has {left} characters left"
            else:
                try:
                    spent += request(job, key)
                    state = True
                except urllib.error.HTTPError as exc:
                    stopped = f"ElevenLabs refused {job['mp3'].name}: HTTP {exc.code} {exc.read().decode(errors='replace')[:300].replace(key, '[REDACTED]')}"
                except Exception as exc:  # network or audio validation: stop spending, keep what exists
                    stopped = f"{job['mp3'].name}: {str(exc).replace(key, '[REDACTED]')[:300]}"
        if state and (args.generate or args.master):
            master(job)
        row = {k: job[k] for k in ("kind", "priority", "speaker", "line", "text")}
        row.update(trigger=job.get("trigger"), voice=job["voice"]["name"], voice_id=job["voice"]["id"], characters=len(job["text"]),
                   cached=bool(state), mp3=str(job["mp3"].relative_to(ROOT)), wav=str(job["wav"].relative_to(ROOT)) if job["wav"].exists() else None)
        if state:
            rec = json.loads(job["record"].read_text())
            row.update(source_sha256=rec["sha256"], response=rec.get("response"), generated_utc=rec.get("generated_utc"))
            if job["wav"].exists():
                row.update(wav_sha256=sha(job["wav"]), seconds=duration(job["wav"]))
        rows.append(row)
        print(f"{'ok  ' if state else '----'} {job['priority']} {job['speaker']}-{job['line']} ({len(job['text'])})", flush=True)
    after = subscription(key) if key else None
    manifest_path = HERE / "voice_manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    runs = previous.get("runs", [])
    if key:
        runs.append({"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "spent_by_cost_header": spent, "budget": args.budget,
                     "subscription_before": before, "subscription_after": after, "stopped": stopped})
    manifest = {"provider": "ElevenLabs", "model_id": MODEL, "output_format": OUTPUT, "voice_settings": SETTINGS,
                "api_reference": "https://elevenlabs.io/docs/api-reference/text-to-speech/convert",
                "mastering": "ffmpeg loudnorm I=-20:TP=-2:LRA=7, mono, 44.1 kHz, PCM16 (as unity/tools/generate_npc_voices.py)",
                "lines": rows, "characters_total": sum(r["characters"] for r in rows),
                "characters_voiced": sum(r["characters"] for r in rows if r["cached"]), "runs": runs}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"spent {spent} characters this run; voiced {manifest['characters_voiced']} of {manifest['characters_total']}")
    if after:
        print(f"subscription after: {after['character_count']}/{after['character_limit']} used")
    if stopped:
        print("STOPPED: " + stopped)


if __name__ == "__main__":
    main()
