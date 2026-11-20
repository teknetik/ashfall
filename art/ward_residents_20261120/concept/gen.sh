#!/usr/bin/env bash
# Concept sheets via codex exec (ChatGPT plan image_gen), as art/ward_walkers_20261003/concept/gen.sh. Usage: gen.sh name [ref.png]
cd "$(dirname "$0")"; n=$1; ref=${2:-}
if [ -n "$ref" ]; then codex exec --skip-git-repo-check -s workspace-write --json -i "$ref" < p_$n.txt > codex_$n.log 2>&1
else codex exec --skip-git-repo-check -s workspace-write --json < p_$n.txt > codex_$n.log 2>&1; fi
echo "$n rc=$? $(ls ${n}_sheet_v*.png 2>&1)"
