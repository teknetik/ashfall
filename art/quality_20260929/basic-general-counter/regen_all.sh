#!/bin/sh
# Full regeneration chain (source .blend -> exports -> QC -> measurements -> review renders -> LOD renders -> sheets -> handoff).
# Textures are generated separately by make_textures.py (slow, deterministic; only re-run when a map changes).
cd /home/teknetik/code/ao2/art/quality_20260929/basic-general-counter || exit 1
sh bl.sh --python build_bgc.py > build_log.txt 2>&1
sh bl.sh --python export_bgc.py > export_log.txt 2>&1
sh bl.sh --python qc_reimport.py > qc_log.txt 2>&1
sh bl.sh --python measure_bgc.py > measure_log.txt 2>&1
sh bl.sh --python render_review.py -- new > render_new.log 2>&1
sh bl.sh --python render_lod.py > render_lod.log 2>&1
sh bl.sh --python compose_sheets.py > compose_log.txt 2>&1
sh bl.sh --python compose_lod.py > compose_lod_log.txt 2>&1
env -i HOME="$HOME" PATH=/usr/bin:/bin /usr/bin/python3 make_handoff.py > handoff_log.txt 2>&1
echo CHAIN_DONE > chain_done.txt
