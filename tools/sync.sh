#!/usr/bin/env bash
# Push repo (code/scripts) to the Linux PC. Generated content lives only on the PC.
set -e
cd "$(dirname "$0")/.."
rsync -az --exclude .git --exclude 'GTAIndia/Content' --exclude 'GTAIndia/Binaries' \
  --exclude 'GTAIndia/Intermediate' --exclude 'GTAIndia/Saved' --exclude 'GTAIndia/DerivedDataCache' \
  ./ linux:gta-india/repo/
ssh linux 'mkdir -p ~/gta-india/GTAIndia && rsync -a ~/gta-india/repo/GTAIndia/ ~/gta-india/GTAIndia/ 2>/dev/null || true'
