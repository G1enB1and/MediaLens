from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

try:
    from app.mediamanager.ai_captioning.local_captioning import LocalAiSettings, WdSwinV2Tagger
except ModuleNotFoundError:
    from local_captioning import LocalAiSettings, WdSwinV2Tagger


def _settings_from_json(raw: str) -> LocalAiSettings:
    payload = json.loads(raw or "{}")
    if "models_dir" in payload:
        payload["models_dir"] = Path(payload["models_dir"])
    return LocalAiSettings(**payload)


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated WD SwinV2 local AI tagging task.")
    parser.add_argument("--operation", choices=("tags", "description", "preload"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    parser.add_argument("--tags-json", default="[]")
    args = parser.parse_args()

    try:
        if args.operation == "preload":
            settings = _settings_from_json(args.settings_json)
            with contextlib.redirect_stdout(sys.stderr):
                WdSwinV2Tagger(settings)
            print(json.dumps({"ok": True}, ensure_ascii=False), flush=True)
            return 0
        if args.operation != "tags":
            raise RuntimeError("WD SwinV2 Tagger v3 can generate tags only.")
        settings = _settings_from_json(args.settings_json)
        with contextlib.redirect_stdout(sys.stderr):
            tags = WdSwinV2Tagger(settings).generate(Path(args.source), settings)
        print(json.dumps({"ok": True, "tags": tags}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
