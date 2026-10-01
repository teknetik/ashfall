#!/usr/bin/env python3
"""Review cameras for the shade sails (player eye 1.65 m unless noted), written to review-cameras.json and created by
ShadeSailsPass (scene root "Shade sail review cameras", disabled Camera components) for the combined native lookbook.
fov = vertical field of view in degrees (Unity Camera.fieldOfView)."""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spawn_dir = (-math.cos(math.radians(17)), -math.sin(math.radians(17)), 0.0)   # FollowCamera yaw -90, pitch 17
CAMS = {
    "cam_ss_courtyard_under": dict(pos=[4.9, 1.65, -8.4], target=[10.2, 3.3, -14.2], fov=60,
                                   note="under the north hem: the madder underside, festoons and the terminals"),
    "cam_ss_courtyard_side": dict(pos=[1.2, 1.65, -19.2], target=[7.8, 3.1, -12.0], fov=55,
                                  note="from the hall side: the whole sail, SW pole, guys and the slab"),
    "cam_ss_market_rest": dict(pos=[-31.6, 1.65, -2.9], target=[-29.6, 2.9, -10.2], fov=60,
                               note="from the market entrance: the indigo sail over the rest spot, the barrel by its hem"),
    "cam_ss_market_lane": dict(pos=[-26.5, 1.65, -15.4], target=[-30.4, 3.4, -7.4], fov=55,
                               note="from the service lane: band clamps on the service pole, the lane festoon"),
    "cam_ss_apron_spawn": dict(pos=[47.0, 2.73, 0.0], target=[47.0 + spawn_dir[0] * 10, 2.73 + spawn_dir[1] * 10, 0.0], fov=50,
                               note="the follow camera's first frame at the West Gate spawn"),
    "cam_ss_apron_goods": dict(pos=[36.2, 1.65, 3.0], target=[37.6, 3.5, 9.4], fov=60,
                               note="under the south hem towards the caravan goods and arch B"),
    "cam_ss_lattice_approach": dict(pos=[0.6, 1.65, -22.4], target=[0.6, 3.0, -33.5], fov=60,
                                    note="walking to the Lattice: the ring framed under the sail's high corner"),
    "cam_ss_lattice_court": dict(pos=[8.6, 1.65, -31.0], target=[0.4, 3.4, -28.2], fov=55,
                                 note="from the east of the court: the sail against the hall"),
}
(HERE / "review-cameras.json").write_text(json.dumps(CAMS, indent=1))
print(len(CAMS), "cameras")
