import json
import sys
from pathlib import Path

from app.mediamanager.metadata import inspect_file


def _print_summary(report: dict) -> None:
    for name, item in report.items():
        canonical = item["canonical"]
        print(f"FILE: {name}")
        print(f"  families: {', '.join(canonical['metadata_families_detected']) or '(none)'}")
        print(f"  source_formats: {', '.join(canonical['source_formats']) or '(none)'}")
        print(f"  tool_found: {canonical['tool_name_found'] or '(none)'}")
        print(f"  tool_inferred: {canonical['tool_name_inferred'] or '(none)'}")
        print(f"  ai_detected: {canonical['is_ai_detected']} confidence={canonical['is_ai_confidence']}")
        if canonical["ai_prompt"]:
            print(f"  prompt: {canonical['ai_prompt'][:180].replace(chr(10), ' ')}")
        if canonical["ai_negative_prompt"]:
            print(f"  negative: {canonical['ai_negative_prompt'][:180].replace(chr(10), ' ')}")
        if canonical["model_name"]:
            print(f"  model: {canonical['model_name']}")
        if canonical["checkpoint_name"]:
            print(f"  checkpoint: {canonical['checkpoint_name']}")
        if canonical["sampler"]:
            print(f"  sampler: {canonical['sampler']}")
        if canonical["scheduler"]:
            print(f"  scheduler: {canonical['scheduler']}")
        if canonical["steps"] is not None:
            print(f"  steps: {canonical['steps']}")
        if canonical["raw_paths"]:
            print(f"  raw_paths: {', '.join(canonical['raw_paths'])}")
        print()


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python scripts/inspect_ai_metadata.py <folder> [--summary]", file=sys.stderr)
        return 1

    root = Path(sys.argv[1])
    report = {}
    for path in sorted(root.iterdir()):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        report[path.name] = inspect_file(path).to_dict()

    if len(sys.argv) == 3 and sys.argv[2] == "--summary":
        _print_summary(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
