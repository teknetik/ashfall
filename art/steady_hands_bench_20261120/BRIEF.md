# Brief (Carl, 20 November 2026, pasted into the session as written)

You are leading a multi-agent team to build a high-fidelity, AAA-quality 3D interactive crafting sequence for the game
Ashfall (Unity). This is the first major crafting quest: "Steady Hands" – creating and fitting a Stabilised Pistol Grip
onto a scrap pistol.

This is not a menu or timer-based craft. It is a game-within-a-game: a hands-on, physical engineering job at Brann's
workbench that should take a player roughly 15–20 minutes of focused interaction and feel like real work.

### Core Requirements
- Full 3D interactivity at the bench.
- Player physically disassembles the scrap pistol.
- Player processes scavenged parts using tools.
- Player fabricates sub-components.
- Player assembles the new Stabilised Pistol Grip with visible plug-together mechanics.
- Player fits the finished grip back onto the pistol.
- Clear before/after difference: the base scrap pistol must feel rough and unstable; the upgraded grip must feel
  meaningfully better (recoil, stability, grouping).
- High production value: models, animations, audio, feedback, and interaction polish to AAA standard.

### Available Tools & Libraries
- Blender (modeling, rigging, animation, export)
- Fal (image/video generation, concept iteration, texture/reference generation)
- ElevenLabs (voice lines, UI/feedback audio, ambient bench sounds)
- AnyMachine library: https://github.com/apekshik/anymachine (use this for complex assembly, constraint, and
  machine-like interaction logic)
- Unity (final integration target)

### Required Deliverables
1. Complete 3D asset set (Blender source + Unity-ready FBX/GLB):
   - Scrap pistol (disassemblable into logical parts)
   - Damaged Servo and other scavenged components
   - Processed versions of those components
   - Stabilised Pistol Grip (and its sub-parts)
   - Workbench, tools (screwdriver, pliers, wire cutters, cleaning tools, etc.), clamps, and interaction props
2. Interaction & assembly system built with AnyMachine (or equivalent constraint/assembly logic) that supports:
   - Grabbing, rotating, and placing parts in 3D
   - Tool use on parts (with appropriate animations and feedback)
   - Snap/plug-together assembly with clear visual and audio confirmation
   - Partial states and mistake recovery
3. Animation set:
   - Pistol disassembly
   - Part processing actions
   - Grip fabrication and assembly
   - Final fitting
   - First-person and third-person compatible where relevant
4. Audio package (ElevenLabs):
   - Tool sounds, mechanical clicks, servo whirs, successful snap, failure/grind
   - Short Brann and Ossa barks for key stages
   - Subtle bench ambience
5. Clear interaction flow and state machine for the full 15–20 minute sequence.
6. Integration notes and prefabs for Unity.

### Sequence Outline (must be fully realised in 3D)
1. Player places scrap pistol on bench and disassembles it (grip and related housing come off).
2. Player processes the Damaged Servo and other materials with tools (clean, trim, rewire, reinforce — multiple short
   physical actions).
3. Player fabricates the new grip components from processed parts.
4. Player assembles the Stabilised Pistol Grip (multiple parts plug together).
5. Player fits the finished grip to the pistol frame.
6. Player can test-handle or dry-fire at the bench before leaving.
7. Strong tactile and audio feedback throughout. Mistakes are recoverable but cost time.

### Quality Bar
- AAA interaction feel (weight, snap, tool feedback, clear affordances).
- No floating menus for the core assembly — physical 3D manipulation is primary.
- Readable at a glance what the player should do next without constant UI hand-holding.
- Performant enough for real-time use in Unity.
- Visually consistent with Ashfall's scavenged industrial aesthetic.

### Execution Instructions
- Break the work across specialised sub-agents (modeling, animation, interaction/AnyMachine logic, audio, Unity
  integration, polish/QA).
- Use Fal for rapid concept and reference generation where helpful.
- Iterate in Blender until the assembly and tool interactions feel solid.
- Document state transitions and AnyMachine setup clearly.
- Deliver a playable prototype sequence (Unity scene or detailed Blender + integration package) that demonstrates the
  full disassemble → process → build → fit loop.

Build this to the standard of a flagship crafting interaction. The player should finish the quest feeling they
actually worked on and improved their pistol, not that they completed a checklist.

Begin by outlining your sub-agent plan and the first assets/interactions you will produce.
