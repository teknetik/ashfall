# Arm survey p2 (2026-11-19 22:45)

Mean (min..max) over 24 samples per clip, both arms pooled; after = with the ArmPoseCorrector state profile. Degrees, cm.
abduction: upper arm out of the body; forward: upper arm reach; elbowOut: elbow turned out (0 = forearm bends forward); palm: 0 = palm to thigh, + = palm back; wrist: total wrist bend; shoulderLift: shoulder height over bind (cm); handOut: hand's lateral distance outside the hip joint (cm).

## player (`player`, profile player, fingers)

| clip | state | abduction | forward | elbowFlex | elbowOut | palm | wrist | shoulderLift | handOut |
|---|---|---|---|---|---|---|---|---|---|
| idle before | idle | 12 (10..14) | -2 (-5..1) | 3 (0..11) | -150 (-150..-150) | -2 (-5..3) | 26 (21..30) | 5 (4..6) | 20 (19..21) |
| idle after | idle | 8 (7..8) | -2 (-5..1) | 12 (12..12) | -28 (-150..0) | 3 (1..7) | 9 (7..11) | 2 (2..2) | 15 (14..16) |
| walk before | walk | 19 (12..27) | 3 (-20..25) | 22 (4..58) | 35 (17..50) | 34 (18..51) | 20 (7..42) | 5 (4..6) | 20 (12..24) |
| walk after | walk | 10 (9..12) | 3 (-20..25) | 24 (15..58) | 22 (0..35) | 14 (11..18) | 8 (3..17) | 2 (2..2) | 13 (9..16) |
| run before | run | 26 (15..35) | -23 (-67..34) | 94 (72..119) | 7 (-16..24) | 17 (-6..41) | 31 (20..51) | 5 (4..6) | 17 (9..29) |
| run after | run | 19 (13..29) | -23 (-67..34) | 94 (72..119) | 9 (-8..17) | 9 (-6..19) | 12 (8..20) | 2 (2..2) | 13 (6..21) |
| jumpTakeoff before | air | 11 (10..12) | -2 (-19..8) | 13 (3..31) | -164 (-176..-149) | -3 (-5..0) | 26 (22..30) | 5 (4..6) | 20 (19..20) |
| jumpTakeoff after | air | 11 (10..12) | -2 (-19..8) | 18 (15..31) | -114 (-173..0) | 6 (-4..21) | 16 (13..18) | 2 (2..2) | 20 (18..26) |
| jumpAirborne before | air | 17 (16..18) | -27 (-30..-24) | 39 (33..45) | -170 (-174..-165) | -7 (-7..-6) | 26 (22..30) | 5 (4..6) | 25 (24..26) |
| jumpAirborne after | air | 17 (16..18) | -27 (-30..-24) | 39 (33..45) | -135 (-137..-133) | 19 (16..23) | 16 (13..18) | 2 (2..2) | 32 (31..33) |
| jumpFall before | air | 23 (21..24) | -20 (-23..-17) | 25 (19..31) | -170 (-175..-164) | -10 (-10..-9) | 26 (22..30) | 5 (4..6) | 30 (29..30) |
| jumpFall after | air | 22 (21..22) | -20 (-23..-17) | 25 (19..31) | -144 (-155..-133) | 15 (12..18) | 16 (13..18) | 2 (2..2) | 32 (30..34) |
| jumpLanding before | air | 11 (10..12) | -10 (-21..1) | 18 (3..33) | -168 (-176..-150) | -3 (-5..0) | 26 (22..30) | 5 (4..6) | 20 (19..20) |
| jumpLanding after | air | 11 (10..12) | -10 (-21..1) | 20 (15..33) | -135 (-172..0) | 11 (-3..21) | 16 (13..18) | 2 (2..2) | 21 (18..26) |
| jumpLandingMoving before | air | 26 (21..33) | -33 (-62..4) | 84 (60..104) | 10 (-9..23) | 16 (-5..41) | 30 (20..38) | -2 (-3..-1) | 15 (5..31) |
| jumpLandingMoving after | air | 25 (21..33) | -33 (-62..4) | 84 (60..104) | 10 (-10..22) | 12 (-1..27) | 18 (12..23) | -2 (-3..-1) | 15 (5..31) |
| pistol_hold before | weapon | -4 (-20..11) | 69 (66..71) | 65 (48..82) | 34 (23..45) | -58 (-92..-25) | 29 (25..34) | 2 (1..3) | -9 (-20..2) |
| rifle_hold before | weapon | 13 (0..25) | 60 (60..61) | 64 (44..84) | 32 (11..52) | -53 (-75..-30) | 38 (38..39) | 8 (7..9) | 7 (-11..25) |
| rifle_carry before | weapon | 31 (21..40) | 19 (5..32) | 49 (34..63) | 27 (5..49) | 26 (12..39) | 30 (26..34) | -2 (-3..0) | 20 (5..34) |
### Pistol (third person), right arm

barrelPitchDown: muzzle below the horizon; barrelYaw: from the body forward (+ = right); turnInHand: how far the pistol is turned inside the hand away from its gripped mount (the grip leaves the palm as this grows); handHeight: above the feet (cm).

| pose | version | abduction | forward | elbowFlex | elbowOut | palm | wrist | barrelPitchDown | barrelYaw | turnInHand | handHeight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pistol_carry_idle | before | 13 | -3 | 2 | - | 0 | 21 | 60 | 0 | 88 | 92 |
| pistol_carry_idle | after | 8 | -3 | 12 | 0 | 13 | 31 | 40 | 0 | 60 | 90 |
| pistol_carry_walk00 | before | 20 (16..27) | 4 (-16..25) | 19 (10..34) | 35 (17..49) | 35 (20..51) | 18 (8..30) | 60 (60..60) | 0 (0..0) | 63 (49..84) | 92 (86..100) |
| pistol_carry_walk00 | after | 11 (10..12) | 4 (-16..25) | 21 (15..34) | 23 (19..31) | 23 (15..29) | 34 (31..38) | 40 (40..40) | 0 (0..0) | 45 (20..72) | 89 (83..97) |
| pistol_carry_walk50 | before | 20 (16..27) | 4 (-16..25) | 19 (10..34) | 35 (17..49) | 35 (20..51) | 18 (8..30) | 60 (60..60) | 0 (0..0) | 63 (49..84) | 92 (86..100) |
| pistol_carry_walk50 | after | 11 (10..12) | 4 (-16..25) | 21 (15..34) | 23 (19..31) | 23 (15..29) | 34 (31..38) | 40 (40..40) | 0 (0..0) | 45 (20..72) | 89 (83..97) |
| pistol_carry_run25 | before | 25 (16..34) | -28 (-67..10) | 96 (81..120) | 3 (-15..18) | 23 (3..41) | 33 (24..50) | 60 (60..60) | 0 (0..0) | 72 (50..101) | 109 (95..123) |
| pistol_carry_run25 | after | 18 (14..24) | -28 (-67..10) | 96 (81..120) | 6 (-8..15) | 10 (-8..28) | 21 (3..32) | 40 (40..40) | 0 (0..0) | 31 (4..69) | 106 (93..121) |
| pistol_raise50 | before | 0 | 51 | 23 | 49 | 13 | 34 | 33 | 17 | 21 | 117 |
| pistol_raise50 | after | 2 | 49 | 51 | 44 | -2 | 16 | 29 | 9 | 15 | 125 |
| pistol_aim_idle | before | -20 | 66 | 48 | 45 | -25 | 24 | 0 | 0 | 0 | 160 |
| pistol_aim_idle | after | -7 | 69 | 47 | 36 | -5 | 29 | 0 | 0 | 0 | 138 |
| pistol_aim_walk25 | before | -20 (-20..-20) | 66 (66..66) | 48 (48..48) | 45 (45..45) | -19 (-22..-16) | 28 (25..30) | 1 (0..1) | -1 (-2..0) | 0 (0..0) | 155 (152..159) |
| pistol_aim_walk25 | after | 4 (-3..12) | 68 (65..73) | 58 (51..65) | 36 (36..37) | -5 (-5..-4) | 24 (22..26) | 1 (0..1) | -1 (-2..0) | 0 (0..0) | 134 (132..136) |


## Notes

- player idle: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..54) -> 83 (83..83)
- player idle: 2 extreme samples, e.g. t0.48R elbow bends backward/outward (-150); t0.52R elbow bends backward/outward (-150)
- player walk: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..54) -> 83 (83..83)
- player walk: arm/opposite-leg swing correlation 0.90 (1 = in phase), arm swing range L/R 47/46 deg
- player run: finger spread 29 (29..29) -> 12 (12..12), curl 53 (53..53) -> 109 (109..109)
- player run: arm/opposite-leg swing correlation 0.93 (1 = in phase), arm swing range L/R 122/92 deg
- player jumpTakeoff: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpTakeoff: 32 extreme samples, e.g. t0.02R elbow bends backward/outward (-150); t0.06R elbow bends backward/outward (-149); t0.10R elbow bends backward/outward (-149); t0.23R elbow bends backward/outward (-149)
- player jumpAirborne: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpAirborne: 48 extreme samples, e.g. t0.02L elbow bends backward/outward (-174); t0.02R elbow bends backward/outward (-165); t0.06L elbow bends backward/outward (-174); t0.06R elbow bends backward/outward (-165)
- player jumpFall: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpFall: 48 extreme samples, e.g. t0.02L elbow bends backward/outward (-175); t0.02R elbow bends backward/outward (-164); t0.06L elbow bends backward/outward (-175); t0.06R elbow bends backward/outward (-164)
- player jumpLanding: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpLanding: 41 extreme samples, e.g. t0.02L elbow bends backward/outward (-175); t0.02R elbow bends backward/outward (-162); t0.06L elbow bends backward/outward (-176); t0.06R elbow bends backward/outward (-164)
- player jumpLandingMoving: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player pistol_hold: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player rifle_hold: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player rifle_carry: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player pistol survey: ok
