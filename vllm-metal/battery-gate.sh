#!/usr/bin/env bash
# AuditBench sample gate for battery-limited Mac hosts: the 140 W MagSafe
# ceiling under-supplies sustained benchmark load (measured ~23%/h net
# drain on the M5 Max), so long campaigns pause between sample batches.
# Defaults are floor 80 / resume 90. The gate never interrupts a sample,
# so a long dense-model batch started just above a low floor can drain far
# below it mid-batch (an audit_deep 4x batch runs an hour and costs ~25%);
# the high default floor makes every batch start near a full charge.
# This host caps charging at 90% for battery health, so a resume level
# above 90 never triggers; 90 is a full reading, not a low one.
# Arguments override per run for campaigns with shorter batches. Inserts
# wait time only; never touches the benchmark. Use via:
#   AUDIT_BENCH_GATE_CMD="vllm-metal/battery-gate.sh [floor] [resume]"
#
# Besides charge, every batch requires a negotiated adapter contract of at
# least 140 W. Twice a weaker supply has contaminated results while macOS
# still reported "charging": the 2026-08-22 USB-PD EPR incident (the Apple
# 140 W brick silently renegotiated 45 W mid-campaign, ~1.4%/min net drain)
# and the 2026-08-21 qwen3.6 canonical, whose decode rows measured ~30% low
# after the battery sagged to 36% mid-run and were only caught by a healthy
# re-measure on 2026-08-24. Charge alone cannot catch a weak contract: the
# battery buffers the deficit and the throttle lands mid-phase.
set -euo pipefail

floor="${1:-80}"
resume="${2:-90}"
watt_min=140

pct() { pmset -g batt | grep -Eo '[0-9]+%' | head -n1 | tr -d '%'; }
watt() { pmset -g ac | grep -Eo 'Wattage = [0-9]+' | grep -Eo '[0-9]+' || echo 0; }

watts="$(watt)"
if [[ "${watts}" -lt "${watt_min}" ]]; then
  echo "gate: adapter contract ${watts} W below ${watt_min} W, waiting for a full-power charger" >&2
  while watts="$(watt)"; [[ "${watts}" -lt "${watt_min}" ]]; do
    sleep 60
  done
  echo "gate: adapter contract ${watts} W, resuming" >&2
fi

charge="$(pct)"
if [[ "${charge}" -ge "${floor}" ]]; then
  exit 0
fi
echo "gate: battery ${charge}% below ${floor}%, waiting for ${resume}%" >&2
while [[ "$(pct)" -lt "${resume}" ]]; do
  sleep 60
done
echo "gate: battery recharged to $(pct)%, resuming" >&2
