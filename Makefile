# Targets that developers, agents and CI share. `make help` lists them.
# On Windows a bare `bash` can resolve to WSL's launcher, so use Git for Windows' bash
# (by its 8.3 path: make's SHELL cannot hold a space) and its tools, such as sed.
ifeq ($(OS),Windows_NT)
SHELL := C:/PROGRA~1/Git/bin/bash.exe
export PATH := C:/PROGRA~1/Git/usr/bin;$(PATH)
else
SHELL := bash
endif
.PHONY: help check test-focused catalog-check dev-db migrate sync serve worker web-check web-types web-e2e

PYTHON_PATHS := src tests scripts migrations
# The one configuration file of the environment (AGENTS.md); a task worktree passes the
# main checkout's absolute path.
ENV_FILE ?= .env.development
export ENV_FILE
TEST_POSTGRES_CONTAINER ?= saudi-api-test-postgres
# Use the PostgreSQL major version that production runs.
TEST_POSTGRES_IMAGE ?= postgres:18
# One `-c name=value` per setting in tests/support/postgres.conf.
TEST_POSTGRES_SETTINGS := $(shell sed -n 's/^\([a-z_]*\) *= *\([^ ]*\).*$$/-c \1=\2/p' tests/support/postgres.conf)

help:
	@printf '%s\n' \
	  'make check                         run Ruff format, Ruff check and ty' \
	  'make test-focused TEST="node ids"  run exact tests on the reused test PostgreSQL' \
	  'make catalog-check                 validate every file in catalog/' \
	  'make dev-db                        start the local PostgreSQL (compose service db)' \
	  'make migrate sync                  apply migrations, then project the catalogue' \
	  'make serve                         run the API service on 127.0.0.1:8000' \
	  'make worker                        run the scheduled jobs until stopped' \
	  'make web-check                     lint and build the web directory' \
	  'make web-types                     regenerate web/openapi.json and its TypeScript types' \
	  'make web-e2e                       run the Playwright tests against a running web and API'

catalog-check:
	uv run --frozen saudi-api catalog check

dev-db:
	docker compose up -d --wait db

migrate:
	uv run --frozen saudi-api migrate

sync:
	uv run --frozen saudi-api catalog sync

serve:
	uv run --frozen saudi-api serve --host 127.0.0.1 --port 8000

worker:
	uv run --frozen saudi-api worker

web-check:
	cd web && npm ci && npm run lint && npm run build

web-types:
	uv run --frozen saudi-api openapi > web/openapi.json
	cd web && npm run generate:api

web-e2e:
	cd web && npx playwright test

check:
	uv run --frozen ruff format --check $(PYTHON_PATHS)
	uv run --frozen ruff check $(PYTHON_PATHS)
	uv run --frozen ty check

# Starts the test PostgreSQL container once and reuses it across runs, worktrees and
# sessions, unless TEST_POSTGRES_DSN points at a server already.
test-focused: export FOCUSED_TEST_TARGETS := $(strip $(TEST))
test-focused:
	@set -euo pipefail; \
	test -n "$$FOCUSED_TEST_TARGETS" || { \
		echo 'TEST is required: pass exact test node IDs (no broad-suite default)' >&2; \
		exit 2; \
	}; \
	for target in $$FOCUSED_TEST_TARGETS; do \
		case "$$target" in *::*) ;; *) echo "not an exact test node ID: $$target" >&2; exit 2 ;; esac; \
		test -f "$${target%%::*}" || { echo "test file does not exist: $${target%%::*}" >&2; exit 2; }; \
	done; \
	if test -z "$${TEST_POSTGRES_DSN:-}"; then \
		container='$(TEST_POSTGRES_CONTAINER)'; \
		case "$$(docker inspect -f '{{.State.Status}}' "$$container" 2>/dev/null)" in \
			exited|created) docker start "$$container" >/dev/null ;; \
			'') docker run -d --name "$$container" --shm-size=1g \
				-e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1::5432 '$(TEST_POSTGRES_IMAGE)' \
				$(TEST_POSTGRES_SETTINGS) >/dev/null ;; \
		esac; \
		for attempt in $$(seq 60); do \
			docker exec "$$container" pg_isready -q -h 127.0.0.1 -U postgres 2>/dev/null && break; \
			test "$$attempt" -lt 60 || { echo "test PostgreSQL $$container is not ready" >&2; exit 1; }; \
			sleep 0.5; \
		done; \
		export TEST_POSTGRES_DSN="postgresql+psycopg://postgres@$$(docker port "$$container" 5432/tcp | head -n 1)/postgres"; \
	fi; \
	uv run --frozen pytest $$FOCUSED_TEST_TARGETS $(PYTEST_ARGS)
