"""Configuração e fixtures partilhadas dos testes automatizados."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ebe_apostilas.core.config import Settings
from ebe_apostilas.core.models import ConteudoApostilaGerado, SecaoGerada, TermoGlossario

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def settings_teste(tmp_path: Path) -> Settings:
    """Configurações isoladas em directório temporário, apontando sempre
    para o mapa curricular oficial real (nunca deve ser copiado/alterado)."""
    return Settings(
        gemini_api_key="test-key-not-real-AIzaFAKE00000000000",
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        logs_dir=tmp_path / "logs",
        assets_dir=REPO_ROOT / "assets",
        state_file=tmp_path / "data" / "estado_producao.json",
        registry_file=tmp_path / "data" / "registro_apostilas.json",
        curriculum_file=REPO_ROOT / "data" / "curriculo_apostilas.json",
    )


@pytest.fixture()
def conteudo_exemplo() -> ConteudoApostilaGerado:
    """Um ``ConteudoApostilaGerado`` completo e válido, usado para testar o
    gerador DOCX sem depender da API Gemini."""
    return ConteudoApostilaGerado(
        titulo="Título de Teste",
        subtitulo="Subtítulo de teste",
        versiculo_chave_texto="Porque Deus amou o mundo de tal maneira...",
        versiculo_chave_referencia="João 3.16",
        texto_base_referencia="João 3.1-21",
        apresentacao="Parágrafo de apresentação 1.\n\nParágrafo de apresentação 2.",
        objectivos=[
            "CONHECER — compreender o tema.",
            "CRER — crer na verdade estudada.",
            "VIVER — aplicar pessoalmente.",
            "SERVIR — servir com o que foi aprendido.",
        ],
        introducao="Parágrafo intro 1.\n\nParágrafo intro 2.\n\nParágrafo intro 3.",
        desenvolvimento=[
            SecaoGerada(titulo="Primeira secção", conteudo="Texto 1.\n\nTexto 2.\n\nTexto 3.\n\nTexto 4."),
            SecaoGerada(titulo="Segunda secção", conteudo="Texto 5.\n\nTexto 6.\n\nTexto 7.\n\nTexto 8."),
            SecaoGerada(titulo="Terceira secção", conteudo="Texto 9.\n\nTexto 10.\n\nTexto 11.\n\nTexto 12."),
            SecaoGerada(titulo="Quarta secção", conteudo="Texto 13.\n\nTexto 14.\n\nTexto 15.\n\nTexto 16."),
        ],
        quadro_destaque_titulo="Para reter",
        quadro_destaque_texto="Uma frase de destaque memorável sobre o tema.",
        aplicacao_pratica=["Aplicação 1", "Aplicação 2", "Aplicação 3", "Aplicação 4", "Aplicação 5"],
        sintese="Parágrafo de síntese 1.\n\nParágrafo de síntese 2.",
        exercicios_compreensao=["Pergunta 1?", "Pergunta 2?", "Pergunta 3?", "Pergunta 4?", "Pergunta 5?"],
        exercicios_reflexao=["Reflexão 1?", "Reflexão 2?", "Reflexão 3?"],
        exercicios_ministerio=["Ministério 1?", "Ministério 2?"],
        estudo_biblico_titulo="Estudo complementar de teste",
        estudo_biblico_texto="Texto introdutório do estudo bíblico complementar.",
        estudo_biblico_perguntas=["E1?", "E2?", "E3?", "E4?", "E5?"],
        resumo_final="Parágrafo de resumo final.",
        glossario=[TermoGlossario(termo=f"Termo {i}", definicao=f"Definição {i}.") for i in range(6)],
        bibliografia=[f"AUTOR {i}. Obra {i}. Cidade: Editora." for i in range(5)],
    )


@pytest.fixture(autouse=True)
def _limpar_pycache():
    yield
    for p in REPO_ROOT.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
