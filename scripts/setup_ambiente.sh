#!/usr/bin/env bash
# ==========================================================================
# Configura o ambiente Python local para desenvolvimento e execução da
# plataforma EBE Apostilas.
# ==========================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Repositório: $REPO_ROOT"
echo "==> Criando ambiente virtual em '$VENV_DIR' (se necessário)..."
"$PYTHON_BIN" -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Actualizando pip..."
pip install --upgrade pip --quiet

echo "==> Instalando dependências de produção..."
pip install -r requirements.txt --quiet

if [[ "${1:-}" == "--dev" ]]; then
  echo "==> Instalando dependências de desenvolvimento..."
  pip install -r requirements-dev.txt --quiet
fi

echo "==> Instalando o pacote em modo editável..."
pip install -e . --quiet

echo "==> Validando integridade do mapa curricular oficial..."
python -m ebe_apostilas.cli.main validar-curriculo

if [[ -z "${GEMINI_API_KEY:-}" ]] && [[ ! -f .env ]]; then
  echo ""
  echo "AVISO: GEMINI_API_KEY não está definida e não existe ficheiro .env."
  echo "Copie .env.example para .env e preencha a sua chave gratuita obtida em:"
  echo "  https://aistudio.google.com/apikey"
  echo ""
fi

echo "==> Ambiente pronto. Active-o com: source $VENV_DIR/bin/activate"
