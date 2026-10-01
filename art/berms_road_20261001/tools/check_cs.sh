#!/usr/bin/env bash
# Compile-check Editor C# outside Unity (so a typo never breaks other agents' batch runs): Unity's own Roslyn with the
# last Assembly-CSharp-Editor response file, plus any files given (new or changed). Output goes to the scratch dir.
set -eu
P=/home/teknetik/code/ao2/unity/AthenHill
RSP=$(ls -t $P/Library/Bee/artifacts/*.dag/Assembly-CSharp-Editor.rsp | head -1)
OUT=${TMPDIR:-/tmp}/berms-cs-check; mkdir -p "$OUT"
grep -v '^-out:\|^-refout:\|^-generatedfilesout\|^-errorlog\|^"Assets/AthenHill/Editor/BermsRoadPass' "$RSP" > "$OUT/check.rsp"
for f in "$@"; do echo "\"$f\"" >> "$OUT/check.rsp"; done
echo "-out:\"$OUT/check.dll\"" >> "$OUT/check.rsp"
cd $P
/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/dotnet /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/sdk/8.0.318/Roslyn/bincore/csc.dll /nologo @"$OUT/check.rsp" 2>&1 | grep -v "warning" | head -40
echo "exit ${PIPESTATUS[0]}"
