#!/usr/bin/env bash
# ==========================================================================
# Executa localmente uma geração de lote de apostilas pendentes, usando as
# variáveis de ambiente definidas em .env (nunca comitar este ficheiro).
#
# Uso:
#   ./scripts/gerar_lote_local.sh            # usa APOSTILAS_POR_EXECUCAO (padrão 11)
#   ./scripts/gerar_lote_local.sh 5          # gera até 5 apostilas
# ==========================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

QUANTIDADE="${1:-}"

if [[ -n "$QUANTIDADE" ]]; then
  python -m ebe_apostilas.cli.main gerar-lote --quantidade "$QUANTIDADE" --workflow "manual-local"
else
  python -m ebe_apostilas.cli.main gerar-lote --workflow "manual-local"
fi
