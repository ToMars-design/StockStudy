#!/usr/bin/env bash
# SessionStart hook: give Claude Code on the web a ready environment, so that
# `make check` works from the first message. Local sessions are left untouched.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:?}"

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --quiet --user uv
  export PATH="$HOME/.local/bin:$PATH"
  echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >>"${CLAUDE_ENV_FILE:?}"
fi

# --locked: fail loudly if uv.lock is stale instead of silently re-resolving.
uv sync --locked
uv run --locked pre-commit install
