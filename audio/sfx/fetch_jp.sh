#!/bin/bash
# Downloads the Japanese free sound effects used by pixel/sfx.py into audio/sfx/jp/ (git-ignored).
# Both sites allow free commercial use in videos without credit, but forbid redistributing the files themselves,
# so they are never committed: run this script to rebuild.
#   ピコピコステーション https://picopico-station.com/terms/ (commercial OK, no credit, editing OK, no redistribution)
cd "$(dirname "$0")" && mkdir -p jp && cd jp
P=https://picopico-station.com/audio
for n in poyon sparkle coin item jump hit balloon-pop heartbeat drone popup decide swoosh powerup levelup tap toggle-on; do
  f=pico_$n.mp3; [ -s $f ] || curl -sS -m 60 -L -A "Mozilla/5.0" -o $f "$P/$n.mp3"
done
ls | wc -l
