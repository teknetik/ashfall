"""Short pronunciation probes in the installed voice: TTS a phrase, transcribe it. Usage: probe_pron.py 'phrase' ..."""
import json, sys, uuid, urllib.request
from pathlib import Path
from el import key
V = json.load(open("voice.json"))["default_voice"]; S = json.load(open("voice.json"))["default_settings"]
k = key()
for i, phrase in enumerate(sys.argv[1:]):
    body = {"text": phrase, "model_id": "eleven_multilingual_v2", "voice_settings": S}
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{V}?output_format=mp3_44100_128", data=json.dumps(body).encode(), headers={"xi-api-key": k, "Content-Type": "application/json"})
    audio = urllib.request.urlopen(req, timeout=120).read()
    f = Path("probe/pron") / f"{uuid.uuid4().hex[:8]}.mp3"; f.write_bytes(audio)
    b = uuid.uuid4().hex
    data = (f"--{b}\r\nContent-Disposition: form-data; name=\"model_id\"\r\n\r\nscribe_v1\r\n--{b}\r\nContent-Disposition: form-data; name=\"language_code\"\r\n\r\neng\r\n--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n").encode() + audio + f"\r\n--{b}--\r\n".encode()
    t = json.load(urllib.request.urlopen(urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=data, headers={"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={b}"}), timeout=120))["text"]
    print(f"{phrase!r:55} -> {t!r}  ({f.name})")
