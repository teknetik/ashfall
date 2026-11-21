#!/usr/bin/env bash
# Reference images through the Grok CLI's image tools (Carl, 20 Nov 2026: "for 2d art you can ask grok at the cli").
# A second route beside OpenAI gpt-image-2. Tested 20 Nov: a six-view sheet in about 30 s, 1248x832 JPEG.
#
# Usage: grok_image.sh OUT.jpg PROMPT.txt [ASPECT] [REF_IMAGE ...]
#   ASPECT: 1:1, 16:9, 9:16, 3:2 (default), 2:3 or auto.
#   With REF_IMAGE(s) the image_edit tool is used (references are downscaled to about 768 px by the service, so they
#   carry shape, identity and colour, not fine detail). Without, image_gen.
# Writes OUT.jpg, OUT.jpg.prompt.txt and OUT.jpg.json (session id, cost, reply). Refuses to overwrite.
# The prompt is sent verbatim. If the service refuses it, stop and say so: do not reword to get round a refusal.
#
# How it is held: headless Grok with ONLY its image tool available (shell, MCP, web and subagents off), run from an
# empty folder outside the repository so no project file is read or sent. Auto-approval applies to that one tool.
set -euo pipefail
[ $# -ge 2 ] || { sed -n 2,9p "$0"; exit 2; }
OUT=$(realpath -m "$1"); PROMPT=$(realpath "$2"); ASPECT="${3:-3:2}"; shift 2; [ $# -gt 0 ] && shift
[ -e "$OUT" ] && { echo "refusing to overwrite $OUT"; exit 2; }
WORK="$HOME/.local/state/ward-programme/steady-hands-20261120/grok-work"; mkdir -p "$WORK" "$(dirname "$OUT")"
ASK=$(mktemp "$WORK/ask.XXXXXX"); RES=$(mktemp "$WORK/res.XXXXXX"); STAMP=$(mktemp "$WORK/stamp.XXXXXX")
if [ $# -gt 0 ]; then
  { echo "Call the image_edit tool exactly once with aspect_ratio \"$ASPECT\", with these reference images (absolute paths):"
    for r in "$@"; do echo "- $(realpath "$r")"; done
    echo; echo "and with this prompt, used verbatim:"; echo; cat "$PROMPT"; echo
    echo "Then reply with only the absolute path of the image the tool produced, and nothing else. Do not run any other tool. If the tool refuses, reply with the single word REFUSED and the reason it gave."; } > "$ASK"
else
  { echo "Call the image_gen tool exactly once with aspect_ratio \"$ASPECT\" and this prompt, used verbatim:"; echo; cat "$PROMPT"; echo
    echo "Then reply with only the absolute path of the image the tool produced, and nothing else. Do not run any other tool. If the tool refuses, reply with the single word REFUSED and the reason it gave."; } > "$ASK"
fi
( cd "$WORK" && timeout 300 grok --prompt-file "$ASK" --max-turns 4 --tools "image_gen,image_edit" --always-approve \
    --deny "Bash" --deny "MCPTool" --disable-web-search --no-subagents --output-format json ) > "$RES" 2>&1 || true
IMG=$(find "$HOME/.grok/sessions" -newer "$STAMP" -type f \( -name '*.jpg' -o -name '*.png' -o -name '*.webp' \) -path '*grok-work*' 2>/dev/null | sort | tail -1)
python3 - "$RES" "$OUT.json" <<'PY'
import json,sys
s=open(sys.argv[1]).read(); i=s.find('{'); d={}
try: d=json.loads(s[i:])
except Exception: d={'raw':s[-1500:]}
keep={k:d.get(k) for k in ('text','stopReason','sessionId','num_turns','total_cost_usd','raw') if k in d}
keep['preamble']=s[:i].strip()[:500] if i>0 else ''
json.dump(keep,open(sys.argv[2],'w'),indent=1); print(keep.get('text') or keep)
PY
rm -f "$ASK" "$RES" "$STAMP"
[ -n "$IMG" ] || { echo "no image produced (see $OUT.json)"; exit 1; }
cp "$IMG" "$OUT"; cp "$PROMPT" "$OUT.prompt.txt"; echo "wrote $OUT"
