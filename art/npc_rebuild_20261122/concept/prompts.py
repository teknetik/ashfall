#!/usr/bin/env python3
"""Concept sheet prompts: the hero base's prompt (art/hero_base_20261120/concept/p_hero_sheet_v1.txt) with the person
changed. Existing prompt files are never overwritten."""
from pathlib import Path
H = Path(__file__).resolve().parent

HEAD = ("Character turnaround sheet for a AAA video game: one wide 16:9 image on a plain neutral mid-grey studio background with soft, "
"even, flat frontal light (no rim light, no dramatic shadows, no cast shadows on the background, no baked highlights). The SAME person is "
"shown three times, full body from the top of the head to the soles of the shoes with the feet fully visible, evenly spaced with clear empty "
"gaps so the figures never overlap or touch each other: (1) FRONT view facing the camera, (2) exact SIDE profile facing right, (3) BACK view. "
"Orthographic-style, camera at chest height, no perspective distortion, all three figures at the same height and scale, each as tall as the "
"frame allows. No dividing lines between the views.\n\n"
"Pose, identical in all three views: standing straight in a relaxed A-pose, arms straight and held about 35 degrees away from the body, hands "
"open and relaxed with the palms facing the thighs and the fingers slightly spread, legs straight and shoulder-width apart with a clear gap "
"of background between them, feet pointing forward, head level, eyes open and looking forward, mouth closed.\n\n")
TAIL = ("\n\nThe setting is a desert oasis colony centuries after its industry collapsed: sun-faded, dusty, mended, but cared for. Photoreal, "
"AAA open-world game character quality: realistic skin pores, natural hands with five separate fingers, individual grey hairs, believable "
"fabric weave, folds and stitching. The garments must be close to the body, so nothing hangs between or over the legs, nothing dangles and "
"no hair rests on the shoulders or chest. NOT stylised, NOT cartoon, NOT low-poly. No text, no labels, no logos, nothing held in the hands, "
"no props, no floor line.")

PEOPLE = {
'linn': """Who she is: LINN, the elder who keeps the memory and the housing roll of a desert city. Use the identity of the woman in the reference image: about 70, dark brown weathered skin, high cheekbones, deep laugh lines and crow's feet, warm, very alert brown eyes with a wry, knowing calm, a strong handsome old face. Silver-white hair braided close to the scalp and wound into a compact bun high on the back of the head, completely clear of the neck and shoulders. Small brass stud earrings and a small matte hearing implant with a tiny cyan light behind one ear.

Build: 1.63 m, lean and wiry, a slightly soft middle, strong old working hands with knuckles and veins, dignified and upright. Not glamorous and not frail.

Clothing (change it from the reference: no long coat, no skirt, no long plait): a fitted, hip-length sleeveless quilted waistcoat of hand-patched faded indigo and ochre cotton with visible sashiko stitching, closed at the front and ending at the hip bone; under it a cream linen shirt with the sleeves neatly rolled to the forearm; a narrow rust-red woven sash wrapped flat at the waist with no hanging ends; a short close necklace of salvaged copper washers and one blue glass bead; tapered charcoal linen trousers; soft brown leather ankle boots with wrapped straps.""",

'brann': """Who he is: BRANN, the salvage dealer and master of the workbench in a desert city. A photoreal, older and more characterful version of the man in the reference image: about 52, big, gruff and shrewd with kind tired eyes, ruddy sun-burnt skin, a broken nose, a short dark crew cut shaved at the sides and going grey at the temples, a big square dark beard heavily streaked with white. He must be clearly a different man from a young action hero: lived-in, heavy, creased.

Build: 1.84 m, a barrel-chested smith with a solid belly, thick neck, massive hairy forearms with old small burn scars, large scarred hands with grime in the knuckles. Realistic proportions, not a bodybuilder.

Clothing: a grey-brown heavy cotton work shirt with riveted leather shoulder patches, sleeves rolled tight above the elbow, worn over a black singlet visible at the open collar; a short scorched brown leather smith's bib strapped tight over the chest and belly and ending at the belt; a wide leather tool belt with two small flat pouches tight at the back of the hips; dark olive double-knee canvas work trousers with oil stains; heavy scuffed steel-toe boots. No gloves, no weapons.""",

'ossa': """Who she is: WARDEN OSSA, the veteran who commands the city gate and trains newcomers. Use the identity and the kit language of the woman in the reference image: about 45, lean weathered face, light olive skin, grey-blue eyes, a hard, level, dryly humorous look, short cropped dark hair heavily streaked with silver, a thin old scar down one cheek, a small temple implant plate with a tiny cyan light.

Build: 1.75 m, athletic, wiry and strong, a soldier's straight back, realistic female proportions.

Clothing: a sun-faded olive field uniform fitted to the body with the sleeves rolled to the elbow; a close canvas plate carrier with one hand-beaten scrap steel plate front and back with riveted edges and chipped ochre hazard paint; one compact riveted steel pauldron on the left shoulder only; a teal cloth Warden band tied flat round the right upper arm with no loose ends; riveted steel bracers on the forearms; fingerless gloves; a webbing belt; an empty slim drop-leg pistol holster strapped tight on the outside of the RIGHT thigh; riveted knee and shin plates; worn laced combat boots. No weapon and no helmet.""",
'mira': """Who she is: MIRA, the keeper of the city's general store. Use the identity of the woman in the reference image: about 42, warm, brisk, quick to smile, light olive-tan sun-weathered skin with freckles and fine lines, hazel eyes, auburn-brown hair pinned in a neat compact bun high on the back of the head, clear of the neck.

Build: 1.68 m, slim and strong from lifting crates, realistic proportions.

Clothing (change it from the reference: no apron below the hips): an off-white linen work shirt with neatly rolled sleeves; a fitted rust-red canvas bib apron with crossed back straps that is cut short and ends at the top of the thighs, wrapped close to the body, with stitched pockets, one indigo patch and a pencil; a small cyan-screened stock tablet fixed flat on the bib; a faded indigo neckerchief tied close; a slim canvas belt; slim tan cotton trousers with a clear gap between the legs; worn brown leather desert boots.""",

'torr': """Who he is: TORR, the city's fixer who keeps its cracked terminals alive. Use the identity of the man in the reference image: about 58, deep tan weathered skin, fully shaved bald head, short salt-and-pepper beard, bushy grey eyebrows, brown eyes, big laugh lines, a small scar on the chin, an amused look. Brass-rimmed magnifier goggles pushed up on his forehead.

Build: 1.76 m, stocky, round-shouldered, a slight belly, thick forearms.

Clothing: a faded indigo mechanic's shirt with the sleeves rolled to the elbow; a short sand canvas tool waistcoat closed at the waist, with screwdrivers, a soldering pen and a small coil of cable held flat in its chest pockets; a salvaged wrist computer with a dim cyan screen on the LEFT forearm; a leather belt; khaki work trousers with grease stains; scuffed work boots. Bare hands, nothing hanging from the belt.""",

'vex': """Who he is: VEX, a volunteer guard at the city's gate. Use the identity of the man in the reference image: about 32, lean, alert, friendly but tough, sun-browned skin of South Asian and European heritage, brown eyes, short dark curly hair with an undercut, short stubble, a thin scar through one eyebrow.

Build: 1.80 m, athletic and wiry, realistic proportions.

Clothing: light gate-guard kit: a fitted sand quilted canvas jacket ending at the hip, sleeves rolled, with a few small riveted scrap-steel plates on the shoulders; a faded teal band round the left upper arm; an olive scarf wrapped close and low round the collar, leaving the whole neck and jaw visible; a utility belt with small pouches; a closed canvas holster high on the right hip; fingerless gloves; olive cargo trousers; laced tan boots.""",

'rell': """Who he is: WARDEN RELL, a young checkpoint sentry. Use the identity of the man in the reference image: about 28, calm and watchful, dark brown skin, dark eyes, close-cropped black hair with a neat fade, short trimmed beard, a thin implant line with a tiny cyan light behind the right ear, bare head (no helmet, no head band).

Build: 1.88 m, tall, rangy, broad-shouldered.

Clothing: a sand field shirt with rolled sleeves; a close sand-tan canvas plate carrier with one riveted steel front plate with chipped teal paint and ochre hazard stripes, plain canvas on the back, three flat magazine pouches; one plain rifle sling strap drawn tight diagonally across chest and back with no rifle; small riveted scrap-steel pads on both shoulders; plate bracers; fingerless gloves; olive canvas trousers; riveted shin plates; worn boots with steel toe caps.""",

'tamsin': """Who she is: TAMSIN, a retired desert caravan outfitter who runs the field-gear shop. Use the identity of the woman in the reference image: about 58, handsome and formidable, deep tan sun-weathered skin, grey-green eyes, a thin old scar through the left eyebrow, steel-grey hair shaved short at the sides with the top braided back tight to the scalp and pinned in a small knot, nothing down the back. Faded geometric route tattoos on both forearms.

Build: 1.76 m, broad-shouldered, sturdy, strong forearms.

Clothing: a faded ochre short-sleeved cotton shirt; a close olive-drab quartermaster's vest of stitched webbing with small flat pouches and a small cyan-lit data slate fixed flat on the chest; an indigo-and-ochre woven sash wrapped flat at the waist with no hanging ends; fingerless brown leather gloves; sand canvas trousers with reinforced knees; worn leather desert boots with buckles. Nothing on the back, no tape measure.""",
}

if __name__ == '__main__':
    for n, body in PEOPLE.items():
        p = H / f'p_{n}_v1.txt'
        if not p.exists():
            p.write_text(HEAD + body + TAIL)
            print('wrote', p.name)
