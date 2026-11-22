#!/usr/bin/env python3
"""Repaint prompt and identity crop (front head of the concept sheet) for one NPC: prompt.py NAME "who" [VERSION]"""
import subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent
n, who = sys.argv[1], sys.argv[2]; v = sys.argv[3] if len(sys.argv) > 3 else 'v1'
(H / n).mkdir(exist_ok=True)
panel = H.parent / f'concept/{n}/panel_front.png'
w, h = map(int, subprocess.check_output(['identify', '-format', '%w %h', str(panel)]).split())
side = int(h * .19)
subprocess.run(['magick', str(panel), '-crop', f'{side}x{side}+{(w - side) // 2}+{int(h * .018)}', '+repage', '-resize', '1024x1024', str(H / n / 'ref.png')], check=True)
(H / n / 'prompt.txt').write_text(
    "Image 1 is an unlit base-colour render of a game character's head. Repaint Image 1 as a photographic skin and hair "
    "texture while keeping it PIXEL-ALIGNED: exactly the same camera, framing, head angle, silhouette, position and size of "
    "every feature, the same clothing and the same flat grey background. Do not turn, move, zoom, crop, reshape or restyle "
    "anything.\n"
    f"The person is {who}; Image 2 shows their face for identity and colouring only (do not copy its angle or framing).\n"
    "Improve only the surface detail: clear, matching, natural brown or grey eyes as in Image 2, both looking straight "
    "ahead, with clean whites, sharp iris and pupil and defined lids and lashes; natural lips without any blue or white "
    "patches; real pores, fine wrinkles and age spots; crisp individual hairs in the eyebrows, hair and any beard. Remove "
    "every smear, blotch and milky or blue artefact.\n"
    "It stays an albedo texture: perfectly even shadowless lighting, the same overall brightness and skin tone as Image 1, "
    "no highlights, no rim light, no depth of field, no text.")
