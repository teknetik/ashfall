#!/usr/bin/env bash
# Play the Steady Hands bench job yourself on a build, from a COPY of your save (your real save is not touched).
# Usage: unity/tools/play_bench.sh [BUILD_DIR=unity/AthenHill/Builds/batch-sh-real2b]
# 1. The game starts with your save copied into a play folder. Press Continue.
# 2. Come back to this terminal and press Enter: the bench opens with a fresh hands-on job (Brann's guidance on).
#    Press Enter again any time to start a fresh job; type q then Enter to stop.
set -u; R=/home/teknetik/code/ao2; B="${1:-$R/unity/AthenHill/Builds/batch-sh-real2b}"
P=/home/teknetik/.local/state/ward-programme/steady-hands-20261120/carl-play; mkdir -p "$P/save"
SRC="$HOME/.config/unity3d/Free Column/Athen Hill/ward-save.json"
[ -f "$P/save/ward-save.json" ] || cp "$SRC" "$P/save/ward-save.json"
rm -f "$P/command.json" "$P/ack.json"
"$B/AthenHill.x86_64" --athen-qa "$P" -logFile "$P/Player.log" & GAME=$!
echo "Game started (pid $GAME). Press Continue in the game, then Enter here to open the bench."
send() { python3 - "$P" <<'PY'
import json,sys,uuid,pathlib,time
p=pathlib.Path(sys.argv[1]); j={"action":"dev.assembly.open","force":True,"fresh":True,"id":uuid.uuid4().hex}
t=p/'command.tmp'; t.write_text(json.dumps(j)); t.rename(p/'command.json')
for _ in range(200):
    a=p/'ack.json'
    if a.exists():
        try: ack=json.loads(a.read_text())
        except Exception: ack={}
        if ack.get('id')==j['id']:
            print('Bench opened.' if ack.get('success') else 'Refused: '+str(ack.get('error'))); sys.exit()
    time.sleep(.05)
print('No answer from the game (is it still loading?). Press Enter to try again.')
PY
}
while kill -0 $GAME 2>/dev/null; do read -r line || break; [ "$line" = q ] && break; send; done
