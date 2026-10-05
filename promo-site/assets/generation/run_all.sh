#!/usr/bin/env bash
# Runs standalone Codex CLI ($imagegen) jobs in parallel for the Ashfall promo concept pack.
cd "$(dirname "$0")"
date -Is > run-start.txt
mkdir -p logs
for s in "$@"; do
  (
    date -Is > "logs/$s.start"
    codex exec --sandbox workspace-write -C "$PWD" - < "$s.request.md" > "logs/$s.log" 2>&1
    echo "exit=$? $(date -Is)" > "logs/$s.done"
  ) &
done
wait
cat logs/*.done
