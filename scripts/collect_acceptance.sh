#!/usr/bin/env bash
# Read-only service/network acceptance. Writes evidence; never restarts or changes settings.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
stamp=$(date +%Y%m%d-%H%M%S)
out="evidence/phase2/qa/collection-$stamp"
mkdir -p "$out"
for previous in evidence/lan/inventory-laptop*.json; do
  if [ -f "$previous" ]; then cp -p "$previous" "$out/previous-$(basename "$previous")"; fi
done
result=0
for action in inventory status; do
  python3 phase2/network.py "$action" > "$out/$action.txt" 2>&1 || result=1
  cat "$out/$action.txt"
done
python3 phase2/network.py test all > "$out/test-all.txt" 2>&1 || result=1
cat "$out/test-all.txt"
printf 'Aggregate collector exit: %s; original per-command results retained in %s\n' "$result" "$out"
exit "$result"
