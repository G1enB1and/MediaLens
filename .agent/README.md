# Agent Repo Conventions

This file is the canonical location guide for AI agents working in this repository.

## Canonical locations

- Human workflow docs belong in `docs/workflows/`.
- Agent workflow mirrors belong in `.agent/workflows/`.
- Test files belong in `tests/`.
- Log output belongs in `logs/`.
- Temporary or debug files belong in `tmp/` or `.tmp-tests/`.
- Utility scripts belong in `scripts/`.
- End-user release artifacts that are intentionally repo-root files may remain in the root only when the build or app explicitly requires them.

## Root directory policy

Do not create new ad hoc files in the repository root unless one of these is true:

- the file is a standard repo root file such as `README.md`, `pyproject.toml`, `setup.cfg`, or `VERSION`
- the application/build explicitly requires the file to live at the root
- the user explicitly asks for a root-level file

If a task is described only by name, resolve it from the canonical locations first instead of assuming a root file exists.

Examples:

- `build-installer` -> `docs/workflows/build-installer.md` and `.agent/workflows/build-installer.md`
- `version-bump` -> `docs/workflows/version-bump.md` and `.agent/workflows/version-bump.md`

## Placement rules

- New tests: create under `tests/`
- New logs: create under `logs/`
- New temp/debug artifacts: create under `tmp/` unless `.tmp-tests/` is more appropriate
- New documentation: create under `docs/` unless it is a root-level product/release file already established by the repo

## Search order for named workflows

When asked to "run" or "open" a workflow by name, check in this order:

1. `docs/workflows/`
2. `.agent/workflows/`
3. only then consider legacy root-level files
