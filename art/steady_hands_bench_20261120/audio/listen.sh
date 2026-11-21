#!/usr/bin/env bash
# Plays the ten clips that matter most, in order, with the name of each printed first.
# Usage: art/steady_hands_bench_20261120/audio/listen.sh        (Ctrl+C stops)
B=/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/Bench
for f in screw/screw-camout-01 screw/screw-seat-01 screw/screw-turn-02 spin/spin-grind-01 spin/spin-true-01 \
         solder/solder-cold-01 solder/solder-flow-01 tester/tester-buzzer-01 tester/tester-lamp-01 \
         rattle/rattle-shake-01 damper/damper-tick-01 press/press-hiss-01 press/press-knit-01 \
         pulse/pulse-shot-01 pulse/pulse-hit-01 amb/amb-bed-01 Voice/npc_brann-take_bench Voice/npc_brann-card_after_fine; do
  echo "== $f"; ffplay -nodisp -autoexit -loglevel error "$B/$f.wav"; sleep 0.4
done
