#!/usr/bin/env bash
# arms step with the scene snapshot taken after the wait, so the diff shows only this step
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../.." && pwd)
cp --reflink=auto "$R/unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity" "$H/logs/scene-before-arms.unity"
exec "$H/install.sh" arms
