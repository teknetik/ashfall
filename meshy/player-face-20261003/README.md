# Player face retexture (3 Oct 2026)

Meshy `v1/retexture` (pre-approved, AGENTS.md §5) of the MPFB2 player's skin mesh (head, neck, hands; CC0 MakeHuman base
mesh) with `enable_original_uv: true`, PBR, 4k, so the result lands on the MPFB UVs. Input
`art/player_face_20261003/meshy_input/skin_head.glb` (`prep_meshy.py`; the eyeballs ride along with their UVs packed into
an empty corner of the layout so Meshy paints sockets, not holes). Job runner `art/player_face_20261003/meshy_job.py`
(copied from the tutorial-set runner; key from `MESHY_API_KEY`, never recorded).

| Name | Style input | Task | Credits | Result |
| --- | --- | --- | ---: | --- |
| `skin_mv_v1` | multi-view, meshy-7: `concept/face_v1_{front,quarter,side}.png` | `01a101b8-df9c-714f-9f0e-f888716dd885` | 10 | **used** (`make_tex.py`) |
| `skin_img_v1` | single image `concept/face_v1_front.png` | `01a101b8-df96-73e0-862c-db0c6b880d2a` | 10 | candidate, greyer skin |
| `skin_text_v1` | text prompt (in its manifest) | `01a101b8-0693-70c1-b062-d52b3ead2800` | 10 | candidate, thin hair/beard |

Total **30 credits**. Concept: Codex image_gen paint-over of our own clay renders (`art/player_face_20261003/concept/`).
Comparison renders: `art/player_face_20261003/renders/cand_*`.
