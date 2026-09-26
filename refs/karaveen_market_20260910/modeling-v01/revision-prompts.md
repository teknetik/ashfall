# Turnaround revision prompts

Mode: built-in image_gen. These targeted edits follow the initial prompts stored beside the sheets. Original outputs remain in the built-in generated-images directory. The final images are saved in this folder.

## food

Edit target: /home/teknetik/.codex/generated_images/01a08c0f-ad8a-7743-9b4a-a1e4ab71e11e/exec-922fda89-59bf-4d87-a3a2-1407caf70ff1.png

Use case: precise-object-edit. Input image 1 is a market-stall modeling turnaround sheet to correct. Preserve the exact board, title, dimension strip, stock, materials, front panel and back panel. Change ONLY THE CANOPY AND UPPER FRAME in the middle RIGHT SIDE panel to agree with the front and back views: this stall has a symmetrical gable roof with the ridge running front-to-back. In this right-side orthographic elevation, BOTH corner posts end at the same eave height, the visible side eave is horizontal and the ridge above is also horizontal, showing a long rectangular roof plane. The side roof MUST NOT slope downward from one post to the other. Keep the shallow roof ridge height equal to the front and back roof peaks, equal scale and ground baseline. Absolutely no other design changes. Return the entire corrected three-panel high-resolution board.

## provisions

Edit target: /home/teknetik/.codex/generated_images/01a08c0f-ad8a-7743-9b4a-a1e4ab71e11e/exec-0b240931-8e38-4c17-81f1-9be24f0edb58.png

Use case: precise-object-edit. Input image 1 is a market-stall modeling turnaround sheet to correct. Preserve the exact board, title, dimension strip, stock, counters, colors, scale, ground baseline, and the BACK panel roof design. Correct ONLY the canopy and upper frame in the FRONT and RIGHT SIDE panels to match the BACK roof: a symmetrical shallow gable roof with its ridge running front-to-back. FRONT must have the same centred triangular shallow gable silhouette, apex height and horizontal left/right eaves as BACK. RIGHT SIDE is a true side orthographic elevation: BOTH corner posts end at the same eave height, the long side eave is horizontal and ridge above it is horizontal, showing a long rectangular roof plane. The side roof MUST NOT slope downward from one post to the other. Keep all stock and plumbing exactly where they are; no other design changes. Return the entire corrected three-panel high-resolution board.

## repairs

Edit target: /home/teknetik/.codex/generated_images/01a08c0f-ad8a-7743-9b4a-a1e4ab71e11e/exec-3275cea1-06c7-4d1d-b375-e3ba3f697173.png

Use case: precise-object-edit. Input image 1 is a three-view caravan repair stall modeling sheet. Correct only the geometry consistency of the BACK (rightmost) panel and counter placement in the middle RIGHT SIDE panel. Preserve all roof profiles, colors, overall dimensions, labels, composition and the FRONT panel.
The FRONT panel shows a full-width tool rack on the rear wall. Therefore in the BACK panel, the flat, utilitarian metal BACK of that same rack must occupy the full width between the rear posts. Replace the impossible half-width wall and right opening with one full-width rear rack back, dull plain metal panels with restrained bolts, transverse mounting rails and a clipped cable; no tools or extra hose coils displayed on the outside back. Show low storage backs below it consistently with the front. Vendor access is through the open SIDE walls, not the rear. There must be no new rear doorway or duplicate counter at the back.
In the middle RIGHT SIDE panel, the customer-facing workbench belongs near the FRONT corner post (image-left), and the tool rack is at the BACK corner post (image-right). The workbench is only 0.65 m deep within the 2.40 m stall depth. Show at least 1.00 m of clear standing space between the rear of the workbench and the thin rear rack. Keep the vise on the front workbench and the existing full rear rack. Do not join the front workbench and rear rack into an impossible solid cabinet. The open side is the entrance. Return the full corrected high-resolution three-panel sheet, no new inset diagrams or labels.

