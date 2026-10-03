#!/usr/bin/env bash
# Generate the three Warden-kit salvage icons with Codex image generation (no API key). Output: <id>.png (1024 px).
# Then fit_icons.sh trims/fits them to 192 px for UI/Art.
set -u; cd "$(dirname "$0")"
style=$(python3 -c "import json;print(json.load(open('prompts.json'))['style'])")
for id in strap_webbing padded_liner rivet_stock; do
  [ -s "$id.png" ] && continue
  desc=$(python3 -c "import json,sys;print(json.load(open('prompts.json'))['items']['$id'])")
  codex exec --skip-git-repo-check -s workspace-write --json "Generate one image with your image tool and save it as $id.png in the current directory (overwrite). Prompt: $desc $style" > "log_$id.jsonl" 2>&1
done
ls -la *.png
