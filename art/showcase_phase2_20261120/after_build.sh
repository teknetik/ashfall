#!/usr/bin/env bash
# Showcase phase 2: wait for a named phase 2 build to finish, then run one native check on it.
# Usage: after_build.sh BUILD NAME SCRIPT.py [ENV=VALUE ...]   (ATHEN_EXE is added)
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
B="$1"; NAME="$2"; SCRIPT="$3"; shift 3; end=$(( $(date +%s) + 3600 ))
until grep -q "build $B rc=0" "$P2/progress.log"; do [ "$(date +%s)" -gt "$end" ] && { echo "no build $B after an hour"; exit 2; }; sleep 10; done
sleep 5
exec "$P2/native_check.sh" "$NAME" "$SCRIPT" ATHEN_EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64 "$@"
