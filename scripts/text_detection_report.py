from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logs/TextDetection")
    if log_path.is_dir():
        candidates = sorted(log_path.glob("text_detection_*.jsonl"))
        if not candidates:
            print("No log files found.")
            return 1
        log_path = candidates[-1]
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return 1

    route_counts: Counter[str] = Counter()
    final_method_counts: Counter[str] = Counter()
    stage_timings: dict[str, list[float]] = defaultdict(list)
    total_timings: list[float] = []
    detected = 0
    total = 0

    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            total += 1
            payload = json.loads(line)
            if payload.get("detected"):
                detected += 1
            final_method_counts[str(payload.get("final_method") or "none")] += 1
            if "elapsed_ms" in payload:
                total_timings.append(float(payload["elapsed_ms"]))
            stages = payload.get("stages") or []
            route_counts["->".join(str(stage.get("status") or "?") for stage in stages)] += 1
            for stage in stages:
                stage_name = str(stage.get("stage") or "unknown")
                elapsed = stage.get("elapsed_ms")
                if elapsed is not None:
                    stage_timings[stage_name].append(float(elapsed))

    print(f"Log: {log_path}")
    print(f"Entries: {total}")
    print(f"Detected: {detected}")
    if total_timings:
        print(
            "Total ms: avg={:.2f} median={:.2f} max={:.2f}".format(
                statistics.fmean(total_timings),
                statistics.median(total_timings),
                max(total_timings),
            )
        )

    print("Routes:")
    for route, count in route_counts.most_common():
        print(f"  {route}: {count}")

    print("Final methods:")
    for method, count in final_method_counts.most_common():
        print(f"  {method}: {count}")

    print("Stage timings:")
    for stage_name in sorted(stage_timings):
        values = stage_timings[stage_name]
        if not values:
            continue
        print(
            "  {}: avg={:.2f} median={:.2f} max={:.2f}".format(
                stage_name,
                statistics.fmean(values),
                statistics.median(values),
                max(values),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
