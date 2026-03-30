# Dev Workflow (Phase 1)

## Setup
```bash
make setup
```

## Test
```bash
make test
```

## Smoke run
```bash
make run
```

## Tiny ingest demo (optional)
```bash
python3 scripts/demo_ingest.py \
  --add "C:\\Media\\Cats\\a.jpg" \
  --add "C:\\Media\\Dogs\\b.jpg" \
  --select "C:\\Media\\Cats"
```
This is just a quick sanity check for ingest + selection + scoped listing before the UI exists.

## What `make test` does
- Runs full unit test suite (`tests/test_*.py`) via `python tests/dev_check.py`
- Exits non-zero on failure for easy CI/automation use
