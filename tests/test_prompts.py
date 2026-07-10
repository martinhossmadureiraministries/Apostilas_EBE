"""Testes do sistema de prompts de geração de apostilas."""
from __future__ import annotations

from pathlib import Path

from ebe_apostilas.core.curriculum import carregar_curriculo
from ebe_apostilas.gemini.prompts import construir_prompt_apostila

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = REPO_ROOT / "data" / "curriculo_apostilas.json"


def test_prompt_contem_titulo_exacto_da_apostila():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    item = curriculo.obter(427)
    prompt = construir_prompt_apostila(item)
    assert item.titulo in prompt
    assert item.codigo in prompt


def test_prompt_contem_contexto_curricular_completo():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    item = curriculo.obter(1)
    prompt = construir_prompt_apostila(item)
    assert item.nivel_nome in prompt
    assert item.instituto_nome in prompt
    assert item.escola_nome in prompt
    assert item.curso_nome in prompt
    assert item.modulo_nome in prompt


def test_prompts_sao_diferentes_para_apostilas_diferentes():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    item1 = curriculo.obter(1)
    item2 = curriculo.obter(500)
    prompt1 = construir_prompt_apostila(item1)
    prompt2 = construir_prompt_apostila(item2)
    assert prompt1 != prompt2


def test_prompt_reforca_originalidade():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    item = curriculo.obter(1)
    prompt = construir_prompt_apostila(item)
    assert "original" in prompt.lower()
    assert "JSON" in prompt
