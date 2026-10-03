#!/usr/bin/env bash
# Concept sheets via codex exec (ChatGPT plan image_gen). Usage: gen.sh name [ref.png]
cd "$(dirname "$0")"; n=$1; ref=${2:-}
if [ -n "$ref" ]; then codex exec --skip-git-repo-check -s workspace-write --json -i "$ref" < p_$n.txt > codex_$n.log 2>&1
else codex exec --skip-git-repo-check -s workspace-write --json < p_$n.txt > codex_$n.log 2>&1; fi
echo "$n rc=$? $(ls -la ${n}_sheet_v1.png 2>&1)"
