#!/usr/bin/env bash
#works on linux not winows.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend/app"
FRONTEND_DIR="$ROOT_DIR/frontend/main"
VENV_DIR="$ROOT_DIR/.venv"
BACKEND_ENV_FILE="$BACKEND_DIR/.env"

backend_pid=""
frontend_pid=""

cleanup() {
  local exit_code=$?

  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
    wait "${frontend_pid}" 2>/dev/null || true
  fi

  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
    wait "${backend_pid}" 2>/dev/null || true
  fi

  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

if [[ -x "$VENV_DIR/bin/python" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
else
  PYTHON_BIN="python3"
fi

if [[ ! -f "$BACKEND_ENV_FILE" ]]; then
  echo "Backend config missing: $BACKEND_ENV_FILE does not exist."
  echo
  echo "Create it from the example first:"
  echo "  cp backend/app/.env.example backend/app/.env"
  echo
  echo "Then edit backend/app/.env and set at least:"
  echo "  FLASK_SECRET_KEY"
  echo "  EMAIL_HASH_PEPPER"
  echo "  EMAIL_ENC_KEY_B64"
  echo "  LOG_PSEUDO_KEY"
  echo "  MICROSOFT_CLIENT_ID"
  echo "  MICROSOFT_CLIENT_SECRET"
  echo
  echo "Then rerun:"
  echo "  bash scripts/dev.sh"
  exit 1
fi

if ! "$PYTHON_BIN" -c "import msal" >/dev/null 2>&1; then
  echo "Backend dependency missing: python module 'msal' is not installed."
  echo
  echo "Set up the backend once with:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r backend/app/requirements.txt"
  echo
  echo "Then rerun:"
  echo "  bash scripts/dev.sh"
  exit 1
fi

echo "Starting backend on http://localhost:5000"
(
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" app.py
) &
backend_pid=$!

echo "Starting frontend dev server"
(
  cd "$FRONTEND_DIR"
  npm run dev
) &
frontend_pid=$!

echo "Backend PID: ${backend_pid}"
echo "Frontend PID: ${frontend_pid}"
echo "Press Ctrl+C to stop both services."

wait -n "$backend_pid" "$frontend_pid"
