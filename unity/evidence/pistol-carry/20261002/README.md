# Pistol carry pose, 2 October 2026

Carl's playtest screenshot (range, pistol drawn, not aiming) showed the scrap pistol sticking out of the
colonist's hanging hand at about 45 degrees. The pistol has been mounted for the two-handed aim hold since
the 27 Sep character-feel pass; in the hanging idle hand that mount leaves the barrel 26 degrees below level
and yawed 117 degrees out to the side (measured in the Editor, `editor/` captures).

## Audition (Editor, edit mode, idle clip frame 37 %, 1600x1000, three views at player height)

| Set | What | Result |
| --- | --- | --- |
| `carry_none_*` | current build | barrel sideways out of the open hand |
| `carry_45/60/75_*` | hand (wrist) turned so the barrel is 45/60/75 degrees below forward | barrel right, but a 95-117 degree wrist twist |
| `gun_45/60/75_*` | pistol turned in the untouched idle hand | barrel beside the thigh, hand keeps its animation |
| `gripA/B_*` | hold clip's hand bone applied first, then either fix | no gain: the hold clip has no finger animation |

The rig has no finger bones under `RightHand` (fingers are skinned to the hand), so an open hand is what every
pose shows; a gripped hand needs a re-rig and is a character-feel task.

**Chosen:** turn the pistol in the hand (`gun_60`): `PlayerWeaponPose.carryPitch = 60`, `carryAlign = 1`.
While the pistol is drawn and the aim layer is down, `PlayerWeaponPose.LateUpdate` resets the pistol to its
saved mount and turns it onto the colonist's forward pitched 60 degrees down; as the aim layer rises the turn
fades out and the existing hand-to-aim-line alignment takes over. No scene or mount change.

Sheets: `editor/sheet.png` (hand fix), `editor/hands.png`, `editor/hands_gun.png` (pistol fix, chosen),
`editor/hands_grip.png`.

Native verification (batch rifle3, 2 Oct 14:15, development build of the dirty tree at 7fdbd282): the real-input
quest check draws the pistol with 7 at the range apron and captures it standing
(`../rifle-armour/20261002/rifle3/quest/run-a/a-pistol-carry-side.png`, `a-pistol-carry-34.png`): the pistol hangs
muzzle-down beside the thigh. The three plates, first contact and the depot were then shot with the same build, so the
raised hold and hip fire still work.
