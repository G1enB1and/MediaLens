from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

from app.mediamanager.ai_captioning.local_captioning import LocalAiSettings, XComposer2Captioner


def _settings_from_json(raw: str) -> LocalAiSettings:
    payload = json.loads(raw or "{}")
    if "models_dir" in payload:
        payload["models_dir"] = Path(payload["models_dir"])
    return LocalAiSettings(**payload)


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated InternLM XComposer2 local AI description task.")
    parser.add_argument("--operation", choices=("tags", "description"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    parser.add_argument("--tags-json", default="[]")
    args = parser.parse_args()

    try:
        if args.operation != "description":
            raise RuntimeError("InternLM XComposer2 VL 1.8B can generate descriptions only.")
        settings = _settings_from_json(args.settings_json)
        tags = json.loads(args.tags_json or "[]")
        with contextlib.redirect_stdout(sys.stderr):
            description = XComposer2Captioner(settings).generate(Path(args.source), [str(tag) for tag in tags], settings)
        print(json.dumps({"ok": True, "description": description}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())

