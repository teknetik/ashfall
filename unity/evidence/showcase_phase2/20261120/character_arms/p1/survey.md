# Arm survey p1 (2026-11-19 22:32)

Mean (min..max) over 24 samples per clip, both arms pooled; after = with the ArmPoseCorrector state profile. Degrees, cm.
abduction: upper arm out of the body; forward: upper arm reach; elbowOut: elbow turned out (0 = forearm bends forward); palm: 0 = palm to thigh, + = palm back; wrist: total wrist bend; shoulderLift: shoulder height over bind (cm); handOut: hand's lateral distance outside the hip joint (cm).

## player (`player`, profile player, fingers)

| clip | state | abduction | forward | elbowFlex | elbowOut | palm | wrist | shoulderLift | handOut |
|---|---|---|---|---|---|---|---|---|---|
| idle before | idle | 12 (10..14) | -2 (-5..1) | 3 (0..11) | -150 (-150..-150) | -2 (-5..3) | 26 (21..30) | 5 (4..6) | 20 (19..21) |
| idle after | idle | -1 (-5..4) | -3 (-5..0) | 12 (12..12) | -28 (-150..0) | 2 (-2..6) | 9 (7..11) | 1 (1..1) | 7 (4..11) |
| walk before | walk | 19 (12..27) | 3 (-20..25) | 22 (4..58) | 32 (22..38) | 34 (18..51) | 20 (7..42) | 5 (4..6) | 20 (12..24) |
| walk after | walk | 5 (-3..10) | 1 (-21..24) | 24 (15..58) | 22 (0..35) | 14 (11..18) | 8 (3..17) | 1 (1..1) | 8 (2..13) |
| run before | run | 26 (15..35) | -23 (-67..34) | 94 (72..119) | 25 (-7..67) | 17 (-6..41) | 31 (20..51) | 5 (4..6) | 17 (9..29) |
| run after | run | 14 (6..23) | -24 (-68..33) | 94 (72..119) | 16 (-4..30) | 5 (-11..18) | 12 (8..20) | 1 (1..1) | 12 (5..26) |
| jumpTakeoff before | air | 11 (10..12) | -2 (-19..8) | 13 (3..31) | -163 (-174..-150) | -3 (-5..0) | 26 (22..30) | 5 (4..6) | 20 (19..20) |
| jumpTakeoff after | air | -2 (-5..2) | -3 (-21..7) | 18 (15..31) | -114 (-173..0) | 7 (-5..24) | 16 (13..18) | 1 (1..1) | 9 (4..18) |
| jumpAirborne before | air | 17 (16..18) | -27 (-30..-24) | 39 (33..45) | -161 (-165..-157) | -7 (-7..-6) | 26 (22..30) | 5 (4..6) | 25 (24..26) |
| jumpAirborne after | air | 6 (2..9) | -28 (-31..-25) | 39 (33..45) | -132 (-135..-130) | 23 (20..27) | 16 (13..18) | 1 (1..1) | 23 (20..26) |
| jumpFall before | air | 23 (21..24) | -20 (-23..-17) | 25 (19..31) | -161 (-165..-156) | -10 (-10..-9) | 26 (22..30) | 5 (4..6) | 30 (29..30) |
| jumpFall after | air | 11 (7..14) | -22 (-25..-18) | 25 (19..31) | -140 (-151..-129) | 17 (15..20) | 16 (13..18) | 1 (1..1) | 23 (19..28) |
| jumpLanding before | air | 11 (10..12) | -10 (-21..1) | 18 (3..33) | -165 (-174..-150) | -3 (-5..0) | 26 (22..30) | 5 (4..6) | 20 (19..20) |
| jumpLanding after | air | -2 (-5..2) | -12 (-22..-1) | 20 (15..33) | -135 (-172..0) | 14 (-3..24) | 16 (13..18) | 1 (1..1) | 10 (4..18) |
| jumpLandingMoving before | air | 26 (21..33) | -33 (-62..4) | 84 (60..104) | 12 (-104..88) | 16 (-5..41) | 30 (20..38) | -2 (-3..-1) | 15 (5..31) |
| jumpLandingMoving after | air | 25 (21..33) | -33 (-62..4) | 84 (60..104) | 7 (-100..61) | 11 (-6..27) | 18 (12..23) | -2 (-3..-1) | 16 (6..38) |
| pistol_hold before | weapon | -4 (-20..11) | 69 (66..71) | 65 (48..82) | -92 (-172..-12) | -58 (-92..-25) | 29 (25..34) | 2 (1..3) | -9 (-20..2) |
| rifle_hold before | weapon | 13 (0..25) | 60 (60..61) | 64 (44..84) | 3 (-47..52) | -53 (-75..-30) | 38 (38..39) | 8 (7..9) | 7 (-11..25) |
| rifle_carry before | weapon | 31 (21..40) | 19 (5..32) | 49 (34..63) | 18 (1..35) | 26 (12..39) | 30 (26..34) | -2 (-3..0) | 20 (5..34) |
### Pistol (third person), right arm

barrelPitchDown: muzzle below the horizon; barrelYaw: from the body forward (+ = right); turnInHand: how far the pistol is turned inside the hand away from its gripped mount (the grip leaves the palm as this grows); handHeight: above the feet (cm).

| pose | version | abduction | forward | elbowFlex | elbowOut | palm | wrist | barrelPitchDown | barrelYaw | turnInHand | handHeight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pistol_carry_idle | before | 13 | -3 | 2 | - | 0 | 21 | 60 | 0 | 88 | 92 |
| pistol_carry_idle | after | 3 | -4 | 12 | 0 | 3 | 7 | 60 | 0 | 72 | 88 |
| pistol_carry_walk00 | before | 20 (16..27) | 4 (-16..25) | 19 (10..34) | 31 (22..36) | 35 (20..51) | 18 (8..30) | 60 (60..60) | 0 (0..0) | 63 (49..84) | 92 (86..100) |
| pistol_carry_walk00 | after | 8 (7..10) | 3 (-17..24) | 21 (15..34) | 24 (18..30) | 13 (11..17) | 7 (3..12) | 60 (60..60) | 0 (0..0) | 60 (40..83) | 88 (82..95) |
| pistol_carry_walk50 | before | 20 (16..27) | 4 (-16..25) | 19 (10..34) | 31 (22..36) | 35 (20..51) | 18 (8..30) | 60 (60..60) | 0 (0..0) | 63 (49..84) | 92 (86..100) |
| pistol_carry_walk50 | after | 8 (7..10) | 3 (-17..24) | 21 (15..34) | 24 (18..30) | 13 (11..17) | 7 (3..12) | 60 (60..60) | 0 (0..0) | 60 (40..83) | 88 (82..95) |
| pistol_carry_run25 | before | 25 (16..34) | -28 (-67..10) | 96 (81..120) | 21 (8..54) | 23 (3..41) | 33 (24..50) | 60 (60..60) | 0 (0..0) | 72 (50..101) | 109 (95..123) |
| pistol_carry_run25 | after | 14 (10..20) | -29 (-68..9) | 96 (81..120) | 15 (8..26) | 10 (0..17) | 13 (10..20) | 60 (60..60) | 0 (0..0) | 55 (28..88) | 105 (92..120) |
| pistol_raise50 | before | 0 | 51 | 23 | 49 | 13 | 34 | 33 | 17 | 21 | 117 |
| pistol_raise50 | after | -2 | 42 | 23 | 38 | 4 | 31 | 38 | 14 | 17 | 110 |
| pistol_aim_idle | before | -20 | 66 | 48 | -172 | -25 | 24 | 0 | 0 | 0 | 160 |
| pistol_aim_idle | after | -20 | 66 | 48 | -172 | -25 | 24 | 0 | 0 | 0 | 160 |
| pistol_aim_walk25 | before | -20 (-20..-20) | 66 (66..66) | 48 (48..48) | -172 (-172..-172) | -19 (-22..-16) | 28 (25..30) | 1 (0..1) | -1 (-2..0) | 0 (0..0) | 155 (152..159) |
| pistol_aim_walk25 | after | -20 (-20..-20) | 66 (66..66) | 48 (48..48) | -172 (-172..-172) | -19 (-22..-16) | 28 (25..30) | 1 (0..1) | -1 (-2..0) | 0 (0..0) | 155 (152..159) |


## Notes

- player idle: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..54) -> 83 (83..83)
- player idle: 2 extreme samples, e.g. t0.48R elbow bends backward/outward (-150); t0.52R elbow bends backward/outward (-150)
- player walk: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..54) -> 83 (83..83)
- player walk: arm/opposite-leg swing correlation 0.90 (1 = in phase), arm swing range L/R 47/46 deg
- player run: finger spread 29 (29..29) -> 12 (12..12), curl 53 (53..53) -> 109 (109..109)
- player run: arm/opposite-leg swing correlation 0.93 (1 = in phase), arm swing range L/R 122/92 deg
- player jumpTakeoff: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpTakeoff: 32 extreme samples, e.g. t0.02R elbow bends backward/outward (-150); t0.06R elbow bends backward/outward (-150); t0.10R elbow bends backward/outward (-150); t0.23R elbow bends backward/outward (-151)
- player jumpAirborne: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpAirborne: 48 extreme samples, e.g. t0.02L elbow bends backward/outward (-165); t0.02R elbow bends backward/outward (-157); t0.06L elbow bends backward/outward (-165); t0.06R elbow bends backward/outward (-157)
- player jumpFall: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpFall: 48 extreme samples, e.g. t0.02L elbow bends backward/outward (-165); t0.02R elbow bends backward/outward (-156); t0.06L elbow bends backward/outward (-165); t0.06R elbow bends backward/outward (-156)
- player jumpLanding: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player jumpLanding: 41 extreme samples, e.g. t0.02L elbow bends backward/outward (-173); t0.02R elbow bends backward/outward (-161); t0.06L elbow bends backward/outward (-174); t0.06R elbow bends backward/outward (-162)
- player jumpLandingMoving: finger spread 29 (29..29) -> 16 (16..16), curl 53 (53..53) -> 83 (83..83)
- player pistol_hold: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player pistol_hold: 24 extreme samples, e.g. t0.02R elbow bends backward/outward (-172); t0.06R elbow bends backward/outward (-172); t0.10R elbow bends backward/outward (-172); t0.15R elbow bends backward/outward (-172)
- player rifle_hold: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player rifle_carry: finger spread 29 (29..29) -> -, curl 53 (53..53) -> -
- player pistol survey: ok
