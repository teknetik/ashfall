#!/usr/bin/env python3
"""Linn's voice (20 Nov 2026, Carl's playtest note: "Linns voice does not match, should be more older and rough").

Re-voices every line Linn speaks (her four dialogue nodes in Data/npc_linn.asset and her nine barks in
art/showcase_20261119/npc_life/barks.json) in one ElevenLabs voice and masters the takes into the game's paths:

  Audio/ElevenLabs/NpcVoices/npc_linn-<node>.wav   (greeting, hill, housing, housing_leased)
  Audio/ElevenLabs/NpcBarks/npc_linn-<line>.wav    (nine barks)

Existing files keep their path and .meta GUID (nothing else has to change). housing and housing_leased had no take
before; their new WAVs are imported by Unity and bound by AthenHill.Editor.LinnVoicePass20261120 (install).

Run from the repository root:
  python3 art/linn_voice_20261120/linn_voice.py                           # dry run: lines, characters, cache state
  python3 art/linn_voice_20261120/linn_voice.py --generate                # default voice (voice.json): make, master, install
  python3 art/linn_voice_20261120/linn_voice.py --generate --voice <id>   # switch: every line in another voice
  python3 art/linn_voice_20261120/linn_voice.py --master [--voice <id>]   # re-master cached takes only, no API calls
  python3 art/linn_voice_20261120/linn_voice.py --candidate NAME --voice <id> --lines greeting,greet_shade
  python3 art/linn_voice_20261120/linn_voice.py --stt                     # transcribe the installed takes, compare words
  python3 art/linn_voice_20261120/linn_voice.py --rollback                # previous takes back (Amelia), new WAVs removed

Takes are cached per voice under takes/<voice_id>/ with a request record; a cached take is reused only when the text,
voice, model and settings match, so re-running is free and idempotent. Spending stops at --budget (default 6000
characters) or when the subscription has fewer characters left than the next line. The key is read from the
repository .env and never printed or written.
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
import uuid

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "unity/AthenHill/Assets/AthenHill"
AUDIO = ASSETS / "Audio/ElevenLabs"
BARKS = ROOT / "art/showcase_20261119/npc_life/barks.json"
PREVIOUS = HERE / "previous"
TAKES = HERE / "takes"
CANDIDATES = HERE / "candidates"
API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"   # the model every other colonist's takes use
OUTPUT = "mp3_44100_128"
CONFIG = json.loads((HERE / "voice.json").read_text())

# Spoken spelling for the generator only; the caption and dialogue text the player reads are never changed.
SAY = {"Nanofab": "nano-fab", "Karaveen": "Carra-veen"}


def credential():
    m = re.search(r"^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.+)$", (ROOT / ".env").read_text(), re.M)
    if not m:
        raise SystemExit("ELEVENLABS_API_KEY is absent from the project .env")
    return m.group(1).strip().strip("\"'")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def spoken(text, voice_id=None):
    # voice.json may override a spelling per voice ("say"), so each voice's cached takes stay valid.
    say_map = {**SAY, **CONFIG["voices"].get(voice_id, {}).get("say", {})}
    for word, say in say_map.items():
        text = re.sub(r"\b" + word + r"\b", say, text)
    return text


def lines(voice_id=None):
    """Every line Linn speaks, in game order: dialogue nodes first, then barks."""
    asset = (ASSETS / "Data/npc_linn.asset").read_text()
    nodes = yaml.safe_load(asset.split("--- !u!114 &11400000", 1)[1])["MonoBehaviour"]["nodes"]
    out = [dict(kind="dialogue", id=n["id"], text=n["text"], wav=AUDIO / "NpcVoices" / f"npc_linn-{n['id']}.wav") for n in nodes]
    speaker = next(s for s in json.loads(BARKS.read_text())["speakers"] if s["id"] == "npc_linn")
    out += [dict(kind="bark", id=l["id"], text=l["text"], trigger=l["trigger"],
                 wav=AUDIO / "NpcBarks" / f"npc_linn-{l['id']}.wav") for l in speaker["lines"]]
    for l in out:
        l["say"] = spoken(l["text"], voice_id)
    return out


def settings_for(voice_id):
    v = CONFIG["voices"].get(voice_id, {})
    return {**CONFIG["default_settings"], **v.get("settings", {})}


def request_body(line, voice_id):
    return {"text": line["say"], "model_id": MODEL, "voice_settings": settings_for(voice_id)}


def take_paths(line, voice_id, folder=None):
    folder = folder or (TAKES / voice_id)
    stem = f"npc_linn-{line['id']}"
    return folder / f"{stem}.mp3", folder / f"{stem}.json"


def cached(line, voice_id, folder=None):
    mp3, rec = take_paths(line, voice_id, folder)
    if not (mp3.exists() and rec.exists()):
        return False
    old = json.loads(rec.read_text())
    return old.get("voice_id") == voice_id and old.get("request") == request_body(line, voice_id) and old.get("sha256") == sha(mp3)


def subscription(key):
    req = urllib.request.Request(API + "/user/subscription", headers={"xi-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        s = json.load(r)
    return {k: s.get(k) for k in ("tier", "character_count", "character_limit", "next_character_count_reset_unix")}


def generate(line, voice_id, key, folder=None):
    mp3, rec = take_paths(line, voice_id, folder)
    body = request_body(line, voice_id)
    req = urllib.request.Request(f"{API}/text-to-speech/{voice_id}?output_format={OUTPUT}", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            audio = r.read()
            headers = {k: r.headers[k] for k in ("request-id", "history-item-id", "character-cost") if k in r.headers}
            ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs refused {mp3.name}: HTTP {e.code} {e.read().decode(errors='replace')[:400].replace(key, '[REDACTED]')}")
    if len(audio) < 1000 or "audio" not in ctype:
        raise SystemExit("ElevenLabs did not return audio for " + mp3.name)
    mp3.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp3.with_suffix(".tmp.mp3")
    tmp.write_bytes(audio)
    subprocess.run(["ffprobe", "-v", "error", str(tmp)], check=True)
    tmp.replace(mp3)
    rec.write_text(json.dumps({"voice_id": voice_id, "voice_name": CONFIG["voices"].get(voice_id, {}).get("name"),
                               "model_id": MODEL, "output_format": OUTPUT, "request": body, "caption_text": line["text"],
                               "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "response": headers,
                               "sha256": sha(mp3)}, indent=2) + "\n")
    return int(headers.get("character-cost") or len(line["say"]))


def loudness(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    return {"lufs": float(i[-1]) if i else None, "peak_dbfs": float(p[-1]) if p else None}


def probe(path):
    s = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
                                 "-of", "json", str(path)], text=True)
    j = json.loads(s)
    st = j["streams"][0]
    return {"codec": st["codec_name"], "rate": int(st["sample_rate"]), "channels": st["channels"], "seconds": round(float(j["format"]["duration"]), 3)}


def edges(path):
    """Leading and trailing silence (below -45 dBFS) in seconds."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=n=-45dB:d=0.02", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    dur = probe(path)["seconds"]
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    lead = ends[0] if starts and starts[0] <= 0.001 and ends else 0.0
    tail = round(dur - starts[-1], 3) if starts and (len(ends) < len(starts) or ends[-1] >= dur - 0.01) else 0.0
    return {"lead_s": round(lead, 3), "tail_s": tail}


def master(src, dst):
    """Same target as the other colonists (loudnorm I=-20, TP=-2, LRA=7; mono 44.1 kHz PCM16), plus trimmed edges:
    60 ms lead-in, about 150 ms tail, so no first syllable is clipped and no long tail is left. A voice whose take starts
    on breath or room tone (Seer Morganna) is not trimmed at -50 dB, so 40 ms of digital silence is added in front of
    every take (an onset never starts on the first sample)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.06,"
            "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse")
    first = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                            trim + ",loudnorm=I=-20:TP=-2:LRA=7:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(first[first.rindex("{"):first.rindex("}") + 1])
    norm = (f"loudnorm=I=-20:TP=-2:LRA=7:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
            f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    tmp = dst.with_name(dst.stem + ".tmp.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af",
                    trim + "," + norm + ",afade=t=in:d=0.008,areverse,afade=t=in:d=0.03,areverse,adelay=40:all=1",
                    "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(tmp)], check=True)
    # loudnorm on a short line can land a dB off: one plain gain step towards -20 LUFS that never lifts the peak over -2 dBFS.
    m2 = loudness(tmp)
    gain = min(-20.0 - m2["lufs"], -2.0 - m2["peak_dbfs"])
    if abs(gain) > 0.2:
        fixed = dst.with_name(dst.stem + ".tmp2.wav")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp), "-af", f"volume={gain:.2f}dB",
                        "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(fixed)], check=True)
        fixed.replace(tmp)
    tmp.replace(dst)  # same path: the existing .meta (and GUID) is untouched


def keep_previous(all_lines):
    """Copy each existing game take to previous/ once (the 2 Oct / 19 Nov Amelia takes)."""
    PREVIOUS.mkdir(parents=True, exist_ok=True)
    record = PREVIOUS / "previous.json"
    rows = json.loads(record.read_text()) if record.exists() else {}
    for l in all_lines:
        if l["wav"].exists() and l["wav"].name not in rows:
            shutil.copy2(l["wav"], PREVIOUS / l["wav"].name)
            rows[l["wav"].name] = {"path": str(l["wav"].relative_to(ROOT)), "sha256": sha(l["wav"]), "voice": "Amelia",
                                   "voice_id": "ZF6FPAbjXT4488VcRRnw"}
        elif not l["wav"].exists() and l["wav"].name not in rows:
            rows[l["wav"].name] = {"path": str(l["wav"].relative_to(ROOT)), "sha256": None, "voice": None,
                                   "note": "no take before 20 Nov 2026 (unvoiced node)"}
    record.write_text(json.dumps(rows, indent=2) + "\n")


def rollback(all_lines):
    rows = json.loads((PREVIOUS / "previous.json").read_text())
    for l in all_lines:
        row = rows.get(l["wav"].name)
        if row is None:
            continue
        if row["sha256"]:
            shutil.copy2(PREVIOUS / l["wav"].name, l["wav"])
            print("restored", l["wav"].relative_to(ROOT))
        else:
            for p in (l["wav"], Path(str(l["wav"]) + ".meta")):
                if p.exists():
                    p.unlink()
                    print("removed", p.relative_to(ROOT))
    (HERE / "installed.json").unlink(missing_ok=True)
    print("Audio rolled back. The Editor pass rollback (run it BEFORE this step, as rollback.sh does) unvoices the housing nodes:")
    print("  P2/seq.sh install linn_voice-rb AthenHill.Editor.LinnVoicePass20261120.RunBatch rollback")


def words(s):
    s = s.lower().replace("-", " ")
    return re.findall(r"[a-z0-9']+", s)


def stt(all_lines, key):
    """Transcribe the installed takes with ElevenLabs Scribe and compare with the line, word by word."""
    import difflib
    results = []
    for l in all_lines:
        if not l["wav"].exists():
            continue
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"model_id\"\r\n\r\nscribe_v1\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"language_code\"\r\n\r\neng\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{l['wav'].name}\"\r\n"
                f"Content-Type: audio/wav\r\n\r\n").encode() + l["wav"].read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(API + "/speech-to-text", data=body,
                                     headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                text = json.load(r).get("text", "")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"speech-to-text refused: HTTP {e.code} {e.read().decode(errors='replace')[:300].replace(key, '[REDACTED]')}")
        a = words(l["text"])
        b = words(text)
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        diff = [f"{op}: {' '.join(a[i1:i2])} -> {' '.join(b[j1:j2])}" for op, i1, i2, j1, j2 in
                difflib.SequenceMatcher(None, a, b).get_opcodes() if op != "equal"]
        results.append({"file": l["wav"].name, "line": l["text"], "transcript": text, "word_match": round(ratio, 3), "differences": diff})
        print(f"{ratio:.3f} {l['wav'].name}: {text}")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", default=CONFIG["default_voice"], help="ElevenLabs voice id (default: voice.json default_voice)")
    ap.add_argument("--generate", action="store_true", help="call the paid API for missing takes, then master and install")
    ap.add_argument("--master", action="store_true", help="master cached takes of --voice into the game paths, no API calls")
    ap.add_argument("--candidate", help="write test takes of --lines to candidates/<NAME>-<line>.mp3 instead of the game")
    ap.add_argument("--lines", help="comma-separated line ids (default: all)")
    ap.add_argument("--budget", type=int, default=6000, help="characters this run may spend (default 6000)")
    ap.add_argument("--stt", action="store_true", help="transcribe the installed takes and compare them with the text")
    ap.add_argument("--rollback", action="store_true", help="restore the previous takes and remove the new housing takes")
    args = ap.parse_args()
    all_lines = lines(args.voice)
    chosen = [l for l in all_lines if not args.lines or l["id"] in args.lines.split(",")]
    if args.rollback:
        return rollback(all_lines)
    key = credential() if (args.generate or args.candidate or args.stt) else None
    if args.stt:
        res = stt(chosen, key)
        out = ROOT / "unity/evidence/showcase_phase2/20261120/linn_voice/stt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
        return
    voice = args.voice
    total = sum(len(l["say"]) for l in chosen)
    print(f"voice {voice} ({CONFIG['voices'].get(voice, {}).get('name', 'not in voice.json')}), settings {settings_for(voice)}")
    print(f"{len(chosen)} lines, {total} characters")
    before = subscription(key) if key else None
    if before:
        print(f"subscription before: {before['character_limit'] - before['character_count']} characters left")
    folder = (TAKES / voice) if not args.candidate else (HERE / "takes_candidates" / voice)
    spent = 0
    for l in chosen:
        state = cached(l, voice, folder)
        if not state and key:
            left = before["character_limit"] - before["character_count"] - spent
            if spent + len(l["say"]) > args.budget or len(l["say"]) > left:
                raise SystemExit(f"STOP: budget {args.budget} / {left} left would be passed at {l['id']} (spent {spent})")
            spent += generate(l, voice, key, folder)
            state = True
        print(f"{'ok  ' if state else '----'} {l['kind']:8} {l['id']:15} {len(l['say']):4}  {l['say'][:70]}")
    if args.candidate:
        CANDIDATES.mkdir(parents=True, exist_ok=True)
        for l in chosen:
            mp3, _ = take_paths(l, voice, folder)
            if mp3.exists():
                dst = CANDIDATES / f"{args.candidate}-{l['id']}.wav"
                master(mp3, dst)
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(dst), "-c:a", "libmp3lame",
                                "-b:a", "160k", str(dst.with_suffix(".mp3"))], check=True)
                dst.unlink()
    elif args.generate or args.master:
        missing = [l["id"] for l in chosen if not cached(l, voice, folder)]
        if missing:
            raise SystemExit(f"cannot install: no cached take in voice {voice} for {missing}; run with --generate")
        keep_previous(all_lines)
        rows = []
        for l in chosen:
            before_m = loudness(l["wav"]) if l["wav"].exists() else None
            mp3, rec = take_paths(l, voice, folder)
            master(mp3, l["wav"])
            rows.append({"kind": l["kind"], "id": l["id"], "file": str(l["wav"].relative_to(ROOT)), "text": l["text"],
                         "spoken_text": l["say"], "characters": len(l["say"]), "voice_id": voice,
                         "voice_name": CONFIG["voices"].get(voice, {}).get("name"), "settings": settings_for(voice),
                         "request": json.loads(rec.read_text()).get("response"), "before": before_m,
                         "after": {**loudness(l["wav"]), **probe(l["wav"]), **edges(l["wav"])}})
        installed = HERE / "installed.json"
        old = json.loads(installed.read_text()) if installed.exists() else {}
        old.update({"voice_id": voice, "voice_name": CONFIG["voices"].get(voice, {}).get("name"), "model_id": MODEL,
                    "installed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "lines": {r["id"]: r for r in {**{r["id"]: r for r in old.get("lines", {}).values()}, **{r["id"]: r for r in rows}}.values()}})
        installed.write_text(json.dumps(old, indent=2, ensure_ascii=False) + "\n")
        print(f"installed {len(rows)} takes in {voice}")
    if key:
        after = subscription(key)
        log = HERE / "spend.json"
        runs = json.loads(log.read_text()) if log.exists() else []
        runs.append({"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "voice": voice, "candidate": args.candidate,
                     "lines": [l["id"] for l in chosen], "spent_by_cost_header": spent,
                     "left_before": before["character_limit"] - before["character_count"],
                     "left_after": after["character_limit"] - after["character_count"]})
        log.write_text(json.dumps(runs, indent=2) + "\n")
        print(f"spent {spent}; subscription after: {after['character_limit'] - after['character_count']} characters left")


if __name__ == "__main__":
    main()
