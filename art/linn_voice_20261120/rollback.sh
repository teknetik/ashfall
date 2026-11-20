#!/usr/bin/env bash
# Linn's voice, 20 Nov 2026: put the previous takes (Amelia) back and unvoice the two housing nodes again.
# One command from anywhere: art/linn_voice_20261120/rollback.sh
set -euo pipefail
R=/home/teknetik/code/ao2; cd "$R"
# Editor pass first (it clears the two housing references while their clips still exist), then the audio files.
P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120
"$P2/seq.sh" install linn_voice-rollback AthenHill.Editor.LinnVoicePass20261120.RunBatch rollback
python3 art/linn_voice_20261120/linn_voice.py --rollback
echo "Also revert the record edits if wanted: unity/tools/devui/npc_roster.json, unity/tools/devui/test_devui.py, unity/AUDIO.md, art/showcase_20261119/npc_life/barks.json, unity/AthenHill/Assets/AthenHill/Editor/NpcVoiceAudit.cs (Linn 4 -> 2)"
