#!/usr/bin/env bash
# Copy the kit generator scripts to the Linux PC and optionally run a build.
#   tools/blender/sync_kit.sh            -> copy only
#   tools/blender/sync_kit.sh build [N]  -> copy + build all assets in N parallel Blender processes (default 3)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
scp -q "$HERE"/kit_*.py "$HERE"/build_kit.py "$HERE"/verify_fbx.py "$HERE"/kit_overview.py "$HERE"/contact_sheet.py linux:gta-india/repo/tools/blender/
if [[ "${1:-}" == "build" ]]; then
  N="${2:-3}"
  ssh linux "mkdir -p ~/gta-india/assets/kit/_logs && cd ~/gta-india/repo/tools/blender && rm -f ~/gta-india/assets/kit/_manifest_part_*.json && \
    for i in \$(seq 0 $((N-1))); do /snap/bin/blender -b -t 6 --python build_kit.py -- --part \$i/$N > ~/gta-india/assets/kit/_logs/kit_build_\$i.log 2>&1 & done; wait; \
    /snap/bin/blender -b --python build_kit.py -- --merge > ~/gta-india/assets/kit/_logs/kit_merge.log 2>&1; grep -h -E 'ASSET|FAILED|Error' ~/gta-india/assets/kit/_logs/kit_build_*.log"
fi
