#!/usr/bin/env bash
cd /home/teknetik/code/ao2/art/steady_hands_bench_20261120
for i in 0 1 2 3 4 5 6 7; do
  [ -e fixtures/sheets/schematic/s$i.jpg ] && continue
  bash imagegen/grok_image.sh fixtures/sheets/schematic/s$i.jpg fixtures/sheets/schematic/s$i.prompt.txt 16:9 || echo "s$i failed"
done
echo GROK_DONE
