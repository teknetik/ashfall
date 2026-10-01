"""Rooftops review cameras (cam_rt_*): street views at 1.6 m eye height that judge the rooflines from where the player
stands (not from cam_hill). Run as a script to write review-cameras.json for RooftopsPass.cs (Unity adds them as
disabled Camera components under "Rooftops review cameras")."""
import json
from pathlib import Path

CAMS = {
    # along each avenue row at eye height (pitch ~13 deg): the rooflines receding in perspective, as a player sees them.
    # (Closer, steeper views were tried and rejected: within ~10 m of a 9 m facade the parapet hides everything behind it.)
    "cam_rt_west_north": {"pos": [-11.2, 1.62, -23.5], "target": [-18.0, 6.6, -4.0], "fov": 60},
    "cam_rt_west_south": {"pos": [-11.2, 1.62, 23.5], "target": [-18.0, 6.6, 4.0], "fov": 60},
    "cam_rt_east_north": {"pos": [12.8, 1.62, -26.0], "target": [18.5, 6.6, -6.0], "fov": 60},
    "cam_rt_east_south": {"pos": [11.2, 1.62, 23.5], "target": [18.0, 6.6, 4.0], "fov": 60},
    # into the cross streets from the avenue: the service lines overhead, masts, conduit drops and the ladder
    "cam_rt_west_cross": {"pos": [-12.6, 1.62, 0.8], "target": [-24.0, 6.4, -0.5], "fov": 60},
    "cam_rt_east_cross": {"pos": [12.6, 1.62, -0.8], "target": [24.0, 6.4, 0.5], "fov": 60},
}


if __name__ == "__main__":
    out = {k: dict(v) for k, v in CAMS.items()}
    (Path(__file__).resolve().parent / "review-cameras.json").write_text(json.dumps(out, indent=1))
    print("\n".join(out))
