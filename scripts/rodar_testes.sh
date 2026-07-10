#!/usr/bin/env bash
# ==========================================================================
# Executa a suíte completa de testes automatizados, sem exigir a
# GEMINI_API_KEY real (todos os testes usam mocks para a API Gemini).
# ==========================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

export GEMINI_API_KEY="${GEMINI_API_KEY:-chave-fake-apenas-para-testes-automatizados}"

python -m pytest tests/ -v "$@"
