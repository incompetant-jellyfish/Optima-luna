#!/usr/bin/env bash
# Parallel, resumable HTTP download (server throttles each connection, so split it).
# Usage: scripts/pdl.sh URL OUTFILE [CONNECTIONS]
# Re-run the same command to resume after an interruption.
set -u
url=$1; out=$2; n=${3:-8}
size=$(curl -sIL --max-time 60 "$url" | grep -i '^content-length' | tail -1 | tr -dc 0-9)
[ -z "$size" ] && { echo "could not get size of $url"; exit 1; }
chunk=$(( (size + n - 1) / n ))
dir="$out.parts"; mkdir -p "$dir"
echo "$(basename "$out"): $size bytes in $n parts"
for i in $(seq 0 $((n - 1))); do
  (
    start=$((i * chunk)); end=$((start + chunk - 1))
    [ "$end" -ge "$size" ] && end=$((size - 1))
    part="$dir/$i"; want=$((end - start + 1))
    for try in $(seq 1 100); do
      have=$(stat -c%s "$part" 2>/dev/null || echo 0)
      [ "$have" -ge "$want" ] && break
      curl -s --speed-time 60 --speed-limit 500 -r "$((start + have))-$end" "$url" >> "$part"
    done
  ) &
done
wait
for i in $(seq 0 $((n - 1))); do cat "$dir/$i"; done > "$out"
actual=$(stat -c%s "$out")
if [ "$actual" -eq "$size" ]; then rm -rf "$dir"; echo "DONE $out ($size bytes)"
else echo "SIZE MISMATCH $out: $actual != $size — re-run to resume"; exit 1; fi
