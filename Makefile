.PHONY: setup test run push-branch

setup:
	python scripts/setup.py

test:
	python tests/dev_check.py

run:
	python -m app.mediamanager.main

push-branch:
	bash scripts/push_subtree_branch.sh
