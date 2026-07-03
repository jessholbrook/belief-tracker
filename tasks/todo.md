# Code review follow-ups (2026-07-02)

- [x] Replace `eval` in `calculate` with AST-whitelist evaluator (RCE fix)
- [x] Fix WS listener accumulation + wrong-conversation routing + stale refetch (App.tsx)
- [x] Optional shared bearer token (`API_AUTH_TOKEN`) for REST + WS, WS origin check
- [x] Persist tool_use/tool_result blocks so agent keeps context across turns
- [x] Belief extraction via forced tool_use (structured output)
- [x] Wire belief tree: extract sub-beliefs under a node; 404 on bad parent
- [x] Warning event on truncated/iteration-capped runs
- [x] Auto-title conversations from first message
- [x] SQLite WAL + per-conversation asyncio lock
- [x] FastAPI lifespan instead of deprecated on_event; response_model wiring
- [x] Drop no-op cache_control; allow_credentials=False
- [x] stop.sh multi-PID fix; Dockerfile HEALTHCHECK
- [x] Backend pytest suite + GitHub Actions CI (pytest + frontend build)
- [x] (found during work) setup.sh: pick Python ≥ 3.10 — macOS system python3 is 3.9

## Review

- 34 backend tests pass (`pytest`); frontend typechecks + builds (`npm run build`).
- Live smoke test verified: health open, 401 without token, CRUD with token,
  404 on bad belief parent, WS handshake rejected for bad origin (403) and
  missing token (403).
- Schema migration is additive (`api_blocks` column) and idempotent; tested
  against a pre-migration database file.
- Deliberately NOT done: multi-user auth, rate limiting, Dockerfile non-root
  user (Fly volume is root-owned; would break SQLite writes without an
  entrypoint chown — revisit if needed).
