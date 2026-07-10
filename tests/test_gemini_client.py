"""Testes do cliente Gemini: validação de esquema, contagem mínima de
palavras, e comportamento correcto de excepções — usando mocks, nunca
chamando a API real."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from ebe_apostilas.core.config import Settings
from ebe_apostilas.core.curriculum import carregar_curriculo
from ebe_apostilas.gemini.client import GeminiClient, GeracaoConteudoError
from ebe_apostilas.gemini.rate_limiter import RateLimiter

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = REPO_ROOT / "data" / "curriculo_apostilas.json"


def _item_exemplo():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    return curriculo.obter(1)


def _resposta_json_valida_grande() -> str:
    """Gera um payload JSON válido, com texto suficientemente extenso para
    passar na validação de contagem mínima de palavras."""
    paragrafo_longo = " ".join(["palavra"] * 400)
    payload = {
        "titulo": "Título de Teste",
        "subtitulo": "Sub",
        "versiculo_chave_texto": "Texto do versículo",
        "versiculo_chave_referencia": "João 3.16",
        "texto_base_referencia": "João 3.1-21",
        "apresentacao": paragrafo_longo,
        "objectivos": ["CONHECER — a", "CRER — b", "VIVER — c", "SERVIR — d"],
        "introducao": paragrafo_longo,
        "desenvolvimento": [
            {"titulo": f"Secção {i}", "conteudo": paragrafo_longo} for i in range(4)
        ],
        "quadro_destaque_titulo": "Para reter",
        "quadro_destaque_texto": "Frase de destaque.",
        "aplicacao_pratica": ["a1", "a2", "a3", "a4", "a5"],
        "sintese": paragrafo_longo,
        "exercicios_compreensao": ["q1", "q2", "q3", "q4", "q5"],
        "exercicios_reflexao": ["r1", "r2", "r3"],
        "exercicios_ministerio": ["m1", "m2"],
        "estudo_biblico_titulo": "Estudo X",
        "estudo_biblico_texto": paragrafo_longo,
        "estudo_biblico_perguntas": ["e1", "e2", "e3", "e4", "e5"],
        "resumo_final": paragrafo_longo,
        "glossario": [{"termo": f"T{i}", "definicao": f"D{i}"} for i in range(6)],
        "bibliografia": ["A. Obra. Cidade: Ed."] * 5,
    }
    return json.dumps(payload, ensure_ascii=False)


def _resposta_json_valida_pequena() -> str:
    payload = json.loads(_resposta_json_valida_grande())
    payload["apresentacao"] = "Muito curto."
    payload["introducao"] = "Curto."
    for sec in payload["desenvolvimento"]:
        sec["conteudo"] = "Curto."
    payload["sintese"] = "Curto."
    payload["estudo_biblico_texto"] = "Curto."
    payload["resumo_final"] = "Curto."
    return json.dumps(payload, ensure_ascii=False)


@pytest.fixture()
def settings_com_chave(tmp_path: Path) -> Settings:
    return Settings(
        gemini_api_key="test-key-AIzaFAKE00000000000000",
        data_dir=tmp_path / "data",
    )


@pytest.fixture()
def rate_limiter_teste(tmp_path: Path) -> RateLimiter:
    return RateLimiter(rpm=1000, tpm=10_000_000, rpd=1000, estado_path=tmp_path / "rl.json")


def test_client_exige_api_key(tmp_path: Path, rate_limiter_teste: RateLimiter):
    settings_sem_chave = Settings(gemini_api_key="", data_dir=tmp_path / "data")
    with pytest.raises(EnvironmentError):
        GeminiClient(settings_sem_chave, rate_limiter_teste)


def test_client_gera_conteudo_valido(settings_com_chave: Settings, rate_limiter_teste: RateLimiter):
    item = _item_exemplo()
    with patch("ebe_apostilas.gemini.client.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text=_resposta_json_valida_grande())
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(settings_com_chave, rate_limiter_teste)
        conteudo = client.gerar_conteudo_apostila(item)

        assert conteudo.titulo == "Título de Teste"
        assert conteudo.contagem_palavras() > 3200


def test_client_conteudo_insuficiente_tenta_fallback_e_falha(settings_com_chave: Settings, rate_limiter_teste: RateLimiter):
    item = _item_exemplo()
    with patch("ebe_apostilas.gemini.client.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text=_resposta_json_valida_pequena())
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(settings_com_chave, rate_limiter_teste)
        with pytest.raises(GeracaoConteudoError):
            client.gerar_conteudo_apostila(item)


def test_client_json_invalido_lanca_erro(settings_com_chave: Settings, rate_limiter_teste: RateLimiter):
    item = _item_exemplo()
    with patch("ebe_apostilas.gemini.client.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text="{ isto nao é json valido")
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(settings_com_chave, rate_limiter_teste)
        with pytest.raises(GeracaoConteudoError):
            client.gerar_conteudo_apostila(item)


def test_client_erro_nao_recuperavel_nao_tenta_novamente(settings_com_chave: Settings, rate_limiter_teste: RateLimiter):
    item = _item_exemplo()
    with patch("ebe_apostilas.gemini.client.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        erro_400 = genai_errors.ClientError(400, {"error": {"message": "Pedido inválido", "status": "INVALID_ARGUMENT"}})
        mock_instance.models.generate_content.side_effect = erro_400
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(settings_com_chave, rate_limiter_teste)
        with pytest.raises(GeracaoConteudoError):
            client.gerar_conteudo_apostila(item)

        # Não deve ter tentado múltiplas vezes o mesmo modelo (erro não retryable).
        assert mock_instance.models.generate_content.call_count <= 2  # 1 por modelo tentado (principal + fallback)
