#!/usr/bin/env bash
# Generate the Field Supply item icons with Codex image generation (no API key). Output: <icon>.png (1024 px).
# fit_icons.sh then trims/fits them to 192 px for UI/Art/<icon>.png.
set -u; cd "$(dirname "$0")"
style=$(python3 -c "import json;print(json.load(open('prompts.json'))['style'])")
for id in $(python3 -c "import json;print(' '.join(json.load(open('prompts.json'))['items']))"); do
  [ -s "$id.png" ] && continue
  desc=$(python3 -c "import json,sys;print(json.load(open('prompts.json'))['items']['$id'])")
  echo "$(date +%H:%M:%S) $id" >> gen_icons.out
  timeout 600 codex exec --skip-git-repo-check -s workspace-write --json "Generate one image with your image tool and save it as $id.png in the current directory (overwrite). Prompt: $desc $style" > "log_$id.jsonl" 2>&1
  [ -s "$id.png" ] && echo "  ok" >> gen_icons.out || echo "  MISSING" >> gen_icons.out
done
echo "$(date +%H:%M:%S) done" >> gen_icons.out
