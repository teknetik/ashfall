"""Generate and install the seven named NPCs' authored dialogue with ElevenLabs.

Run from the repository root: python3 unity/tools/generate_npc_voices.py --generate
The project .env supplies ELEVENLABS_API_KEY; no credential enters the manifest.
Existing takes are reused only when the recorded text, voice and model match.
Requires PyYAML and ffmpeg/ffprobe. Use --install to restore references offline.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "unity/AthenHill/Assets/AthenHill/Data"
STAGING = ROOT / "unity/staging/elevenlabs-audio/npc-voices"
DEST = ROOT / "unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/NpcVoices"
MODEL = "eleven_multilingual_v2"
OUTPUT = "mp3_44100_128"
ROSTER = json.loads((ROOT / "unity/tools/devui/npc_roster.json").read_text())["npcs"]
VOICES = {row["id"]: (row["voiceName"], row["accent"], row["voiceId"]) for row in ROSTER}


def credential():
    # Read without sourcing shell code or exposing the value in a subprocess/log.
    local = ROOT / ".env"
    common = Path(subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT, text=True).strip()).parent / ".env"
    source = local if local.exists() else common
    content = source.read_text()
    match = re.search(r"^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.+)$", content, re.M)
    if not match:
        raise RuntimeError("ELEVENLABS_API_KEY is absent from the project .env")
    return match.group(1).strip().strip("\"'")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nodes(path):
    content = path.read_text()
    parsed = yaml.safe_load(content.split("--- !u!114 &11400000", 1)[1])["MonoBehaviour"]
    return content, parsed["nodes"]


def audio_meta(guid):
    return f"""fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 8
  defaultSettings:
    serializedVersion: 2
    loadType: 0
    sampleRateSetting: 0
    sampleRateOverride: 44100
    compressionFormat: 1
    quality: 0.85
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 1
  normalize: 0
  loadInBackground: 0
  ambisonic: 0
  3D: 1
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def request_audio(voice_id, line, target, record, key):
    body = {"text": line, "model_id": MODEL, "voice_settings": {"stability": 0.55, "similarity_boost": 0.78, "style": 0.12, "use_speaker_boost": True}}
    expected = {"voice_id": voice_id, "model_id": MODEL, "output_format": OUTPUT, "request": body}
    if target.exists():
        if not record.exists():
            raise RuntimeError(f"Cached take has no request record: {target}")
        old = json.loads(record.read_text())
        if any(old.get(k) != v for k, v in expected.items()) or old.get("sha256") != sha(target):
            raise RuntimeError(f"Cached take differs from the current dialogue: {target}")
        return old
    if key is None:
        raise RuntimeError(f"Missing take: {target}; use --generate")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={OUTPUT}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            audio = response.read()
            headers = {k: response.headers[k] for k in ("request-id", "history-item-id", "character-cost") if k in response.headers}
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ElevenLabs returned HTTP {exc.code}: {exc.read().decode()[:500].replace(key, '[REDACTED]')}") from None
    if len(audio) < 1000 or "audio" not in content_type:
        raise RuntimeError("ElevenLabs did not return an audio file")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.mp3")
    temporary.write_bytes(audio)
    subprocess.run(["ffprobe", "-v", "error", str(temporary)], check=True)
    temporary.replace(target)
    entry = {**expected, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "response": headers, "sha256": sha(target)}
    record.write_text(json.dumps(entry, indent=2) + "\n")
    return entry


def master(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                    "-af", "loudnorm=I=-20:TP=-2:LRA=7", "-ac", "1", "-ar", "44100",
                    "-c:a", "pcm_s16le", str(target)], check=True)


def install_reference(path, node_ids):
    content = path.read_text()
    for node_id, guid in node_ids.items():
        # Keep every original field and choice as serialized; insert after this node's text.
        pattern = re.compile(r"(^  - id: " + re.escape(node_id) + r"\n(?:^(?!  - id: ).*\n)*?^    text: [^\n]*\n)(?:^    voice: [^\n]*\n)?", re.M)
        content, count = pattern.subn(lambda m: m.group(1) + f"    voice: {{fileID: 8300000, guid: {guid}, type: 3}}\n", content, count=1)
        if count != 1:
            raise RuntimeError(f"Could not install voice on {path.name}:{node_id}")
    path.write_text(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Use the paid API for missing takes")
    parser.add_argument("--install", action="store_true", help="Restore asset references from cached takes")
    args = parser.parse_args()
    key = credential() if args.generate else None
    manifest = {"provider": "ElevenLabs", "model_id": MODEL, "output_format": OUTPUT,
                "api_reference": "https://elevenlabs.io/docs/api-reference/text-to-speech/convert", "actors": []}
    for actor_id, (voice_name, accent, voice_id) in VOICES.items():
        path = DATA / f"{actor_id}.asset"
        _, dialogue = nodes(path)
        references = {}
        actor = {"actor": actor_id, "voice": voice_name, "accent": accent, "voice_id": voice_id, "lines": []}
        for node in dialogue:
            name = f"{actor_id}-{node['id']}"
            source = STAGING / f"{name}.mp3"
            record = STAGING / f"{name}.json"
            dest = DEST / f"{name}.wav"
            request_audio(voice_id, node["text"], source, record, key)
            if not dest.exists() or dest.stat().st_mtime < source.stat().st_mtime:
                master(source, dest)
            meta = Path(str(dest) + ".meta")
            guid = re.search(r"^guid: ([0-9a-f]{32})$", meta.read_text(), re.M).group(1) if meta.exists() else uuid.uuid4().hex
            if not meta.exists():
                meta.write_text(audio_meta(guid))
            references[node["id"]] = guid
            actor["lines"].append({"node": node["id"], "text": node["text"], "source_sha256": sha(source),
                                   "wav_sha256": sha(dest), "guid": guid})
            print(f"{name}: {voice_name}, {accent}", flush=True)
        install_reference(path, references)
        manifest["actors"].append(actor)
    STAGING.mkdir(parents=True, exist_ok=True)
    (STAGING / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Installed {sum(len(a['lines']) for a in manifest['actors'])} dialogue takes")


if __name__ == "__main__":
    main()
