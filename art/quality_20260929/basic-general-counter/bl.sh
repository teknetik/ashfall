#!/bin/sh
# Run Blender in a clean environment: the Hermes PATH puts an incompatible python first and breaks Blender's bundled modules.
exec env -i HOME="$HOME" PATH=/usr/bin:/bin blender -b --factory-startup "$@"
