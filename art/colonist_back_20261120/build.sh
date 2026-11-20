#!/usr/bin/env bash
# Colonist back pass (20 Nov 2026): rebuild every output in out/ from source. Steps (each through the phase 2 wrappers):
#  1. suit surface bakes      blender/bake_suit.py -> bake/*.npy
#  2. suit textures           make_suit.py -> tex/suit_base.png, tex/suit_normal.png
#  3. colonist.glb            patch_glb.py: shipped colonist.glb (rollback/colonist.glb once installed) with the two images swapped
#  4. vest/carrier/helmet     fit_all.sh (fit_piece.py fit -> decimate.py -> fit_piece.py skin) -> out/TS_*.glb
#  5. texture calm-down       clean_tex.py + patch_glb.py on the helmet and vest (fitted copies kept in work/fitted/)
#  6. rig check               check_rig.py against the shipped pieces (joint order, inverse bind matrices, names)
set -eu
cd /home/teknetik/code/ao2; A=art/colonist_back_20261120
P2=~/.local/state/ward-programme/showcase-phase2-20261120; H=~/.local/state/ward-programme/heavy.sh
U=unity/AthenHill/Assets/AthenHill/Art
SRC=$U/Imported/Meshy/colonist.glb; [ -f $A/rollback/colonist.glb ] && SRC=$A/rollback/colonist.glb
$P2/blender.sh $A/blender/bake_suit.py -- 4096
uv run --with numpy python $A/edit_suit_mesh.py $SRC $A/work/colonist_mesh.glb $A/work/hem_report.json   # hems (fix round)
$H uv run --with numpy --with pillow --with scipy python $A/make_suit.py                                  # needs hem_report.json
$H uv run --with numpy --with pillow --with scipy python $A/hair_tex.py
python3 $A/patch_glb.py $A/work/colonist_mesh.glb $A/out/colonist.glb suit_base=$A/tex/suit_base.png player_normal_4k=$A/tex/suit_normal.png \
  hair_shell=$A/tex/hair_shell.png skin_rough=$A/tex/skin_rough.png --mat PlayerJumpsuit.normalTexture.scale=0.55 \
  PlayerJumpsuit.pbrMetallicRoughness.roughnessFactor=0.95 PlayerHairShell.pbrMetallicRoughness.roughnessFactor=0.85
$A/fit_all.sh vest carrier helmet
mkdir -p $A/work/fitted; cp $A/out/TS_Helmet.glb $A/out/TS_FieldVest.glb $A/work/fitted/
python3 $A/extract_tex.py $A/work/tex $A/work/fitted/TS_Helmet.glb $A/work/fitted/TS_FieldVest.glb
$H uv run --with numpy --with pillow --with scipy python $A/group_helmet.py $A/work/tex/TS_Helmet
$H uv run --with numpy --with pillow --with scipy python $A/clean_tex.py $A/work/tex/TS_FieldVest 0.5 0.8 0.05
python3 $A/patch_glb.py $A/work/fitted/TS_Helmet.glb $A/out/TS_Helmet.glb Image_0=$A/work/tex/TS_Helmet/group_base.png Image_1=$A/work/tex/TS_Helmet/group_mr.png --mat Material_0.normalTexture.scale=0.6
python3 $A/patch_glb.py $A/work/fitted/TS_FieldVest.glb $A/out/TS_FieldVest.glb Image_0=$A/work/tex/TS_FieldVest/clean_base.png Image_1=$A/work/tex/TS_FieldVest/clean_mr.png --mat Material_0.normalTexture.scale=0.75
R=$U/Armour/TutorialSet; [ -d $A/rollback ] && [ -f $A/rollback/TS_FieldVest.glb ] && R=$A/rollback
python3 $A/check_rig.py $R/TS_FieldVest.glb $A/out/TS_FieldVest.glb $R/TS_Helmet.glb $A/out/TS_Helmet.glb $R/TS_WardenCarrier.glb $A/out/TS_WardenCarrier.glb
