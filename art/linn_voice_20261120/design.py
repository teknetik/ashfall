"""One ElevenLabs voice-design call: three previews of a described voice, saved to probe/design/."""
import base64, json
from pathlib import Path
from el import call
DESC = ("An old woman in her late seventies with a low, dry, rough and slightly gravelly voice, weathered by decades of "
        "desert dust and hard work. She speaks slowly and plainly, unhurried, with quiet authority and a hint of dry humour. "
        "Neutral British accent. Not sweet, not theatrical, not a witch: a tough survivor who has seen her city fall and be "
        "rebuilt. Close, natural, dry studio recording with no reverb.")
TEXT = ("You can see the gate, hear the market, and get out of the dust. No terminal needs to explain that. "
        "If we get separated, meet me on the hill.")
out = Path("probe/design"); out.mkdir(parents=True, exist_ok=True)
r = call("POST", "/v1/text-to-voice/design", {"voice_description": DESC, "text": TEXT, "model_id": "eleven_ttv_v3"})
meta = {"description": DESC, "text": TEXT, "model_id": "eleven_ttv_v3", "previews": []}
for i, p in enumerate(r.get("previews", [])):
    f = out / f"design_{i}_{p['generated_voice_id']}.mp3"
    f.write_bytes(base64.b64decode(p["audio_base_64"]))
    meta["previews"].append({"generated_voice_id": p["generated_voice_id"], "file": f.name, "duration": p.get("duration_secs")})
(out / "design.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta["previews"], indent=1))
