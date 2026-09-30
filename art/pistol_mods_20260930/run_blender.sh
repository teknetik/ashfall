#!/bin/bash
# Usage: ./run_blender.sh script.py [-- args]  (CPU only, memory capped, clean env for the glTF add-on; PM_* vars pass through)
PASS=$(env | grep '^PM_' | tr '\n' ' ')
exec env -i HOME=$HOME PATH=/usr/bin:/bin XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)} DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus} $PASS \
  systemd-run --user --scope -q -p MemoryMax=10G -p MemoryHigh=8G blender -b --factory-startup --python "$@"
