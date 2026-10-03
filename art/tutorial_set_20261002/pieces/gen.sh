#!/usr/bin/env bash
cd "$(dirname "$0")"
while IFS=$'\t' read -r name desc; do
  [ -f "$name.png" ] && continue
  printf '%s\n' "Use your image generation tool. The attached reference sheet shows our game's tutorial armour set (salvaged scrap metal on a crash-repaired flight suit, realistic sci-fi desert colony). Create a product-style reference image of ONE piece, isolated on a plain mid-grey background, soft even studio light with no strong shadows or highlights, sharp detail, realistic PBR look, centred and filling most of the frame, nothing else in frame (no body, no mannequin, no stand, no text, no logo): $desc Square 1024x1024. Save as $name.png in the current directory." > "prompt_$name.txt"
  codex exec --skip-git-repo-check -s workspace-write --json -i ../concept/tutorial_set_concept_v1.png < "prompt_$name.txt" > "codex_$name.log" 2>&1
  echo "$name $( [ -f $name.png ] && echo ok || echo FAIL)"
done < pieces.tsv
echo ALLDONE
