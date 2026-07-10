"""
Cliente Gemini de produção: encapsula a API gratuita do Google Gemini com
retry automático, backoff exponencial, controlo de RPM/TPM/RPD e
tratamento robusto de excepções, devolvendo sempre um
``ConteudoApostilaGerado`` validado ou lançando uma excepção clara.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from ebe_apostilas.core.config import Settings
from ebe_apostilas.core.models import ConteudoApostilaGerado, ItemCurricular
from ebe_apostilas.gemini.prompts import construir_prompt_apostila
from ebe_apostilas.gemini.rate_limiter import LimiteDiarioExcedidoError, RateLimiter

logger = logging.getLogger("ebe_apostilas.gemini_client")

# Aproximadamente 4 caracteres por token — heurística conservadora para
# estimar consumo de TPM antes de cada chamada, evitando ultrapassar a
# quota gratuita.
_CARACTERES_POR_TOKEN_ESTIMADO = 4

_ESQUEMA_RESPOSTA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "subtitulo": {"type": "STRING"},
        "versiculo_chave_texto": {"type": "STRING"},
        "versiculo_chave_referencia": {"type": "STRING"},
        "texto_base_referencia": {"type": "STRING"},
        "apresentacao": {"type": "STRING"},
        "objectivos": {"type": "ARRAY", "items": {"type": "STRING"}},
        "introducao": {"type": "STRING"},
        "desenvolvimento": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "titulo": {"type": "STRING"},
                    "conteudo": {"type": "STRING"},
                },
                "required": ["titulo", "conteudo"],
            },
        },
        "quadro_destaque_titulo": {"type": "STRING"},
        "quadro_destaque_texto": {"type": "STRING"},
        "aplicacao_pratica": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sintese": {"type": "STRING"},
        "exercicios_compreensao": {"type": "ARRAY", "items": {"type": "STRING"}},
        "exercicios_reflexao": {"type": "ARRAY", "items": {"type": "STRING"}},
        "exercicios_ministerio": {"type": "ARRAY", "items": {"type": "STRING"}},
        "estudo_biblico_titulo": {"type": "STRING"},
        "estudo_biblico_texto": {"type": "STRING"},
        "estudo_biblico_perguntas": {"type": "ARRAY", "items": {"type": "STRING"}},
        "resumo_final": {"type": "STRING"},
        "glossario": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "termo": {"type": "STRING"},
                    "definicao": {"type": "STRING"},
                },
                "required": ["termo", "definicao"],
            },
        },
        "bibliografia": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "titulo", "versiculo_chave_texto", "versiculo_chave_referencia",
        "texto_base_referencia", "apresentacao", "objectivos", "introducao",
        "desenvolvimento", "quadro_destaque_texto", "aplicacao_pratica",
        "sintese", "exercicios_compreensao", "exercicios_reflexao",
        "exercicios_ministerio", "estudo_biblico_titulo", "estudo_biblico_texto",
        "estudo_biblico_perguntas", "resumo_final", "glossario", "bibliografia",
    ],
}


class GeracaoConteudoError(Exception):
    """Erro definitivo (após todas as tentativas) na geração de conteúdo
    de uma apostila via Gemini."""


class ConteudoInsuficienteError(Exception):
    """Lançado quando o conteúdo devolvido pelo modelo não atinge o volume
    mínimo exigido (apostila deve ter 15 a 20 páginas reais)."""


_PALAVRAS_MINIMAS = 3200  # limite de segurança para conteúdo textual real


def _retryable_exception(exc: BaseException) -> bool:
    """Determina se uma excepção justifica nova tentativa: erros de
    servidor (5xx), erros de limite de taxa (429) e erros de rede/tempo
    esgotado são elegíveis a retry; erros de autenticação/pedido inválido
    (4xx que não sejam 429) não são retentados."""
    if isinstance(exc, genai_errors.ClientError):
        codigo = getattr(exc, "code", None)
        return codigo == 429
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return False


class GeminiClient:
    """Cliente de alto nível para geração de conteúdo de apostilas,
    aplicando automaticamente retry, backoff exponencial e controlo de
    limites da API gratuita do Gemini."""

    def __init__(self, settings: Settings, rate_limiter: RateLimiter):
        settings.validate_required_for_generation()
        self._settings = settings
        self._rate_limiter = rate_limiter
        self._client = genai.Client(api_key=settings.gemini_api_key)

    @property
    def settings(self) -> Settings:
        """Acesso público e somente-leitura à configuração do cliente."""
        return self._settings

    def _estimar_tokens(self, prompt: str) -> int:
        return max(len(prompt) // _CARACTERES_POR_TOKEN_ESTIMADO, 1) + self._settings.gemini_max_output_tokens

    def _chamar_modelo(self, modelo: str, prompt: str) -> str:
        tokens_estimados = self._estimar_tokens(prompt)
        self._rate_limiter.aguardar_e_reservar(tokens_estimados)

        config = genai_types.GenerateContentConfig(
            temperature=self._settings.gemini_temperature,
            max_output_tokens=self._settings.gemini_max_output_tokens,
            response_mime_type="application/json",
            response_schema=_ESQUEMA_RESPOSTA,
        )

        @retry(
            reraise=True,
            stop=stop_after_attempt(self._settings.retry_max_attempts),
            wait=wait_exponential(
                multiplier=self._settings.retry_backoff_multiplier,
                min=self._settings.retry_initial_backoff_seconds,
                max=self._settings.retry_max_backoff_seconds,
            ),
            retry=retry_if_exception_type(
                (genai_errors.ClientError, genai_errors.ServerError, TimeoutError, ConnectionError)
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _executar() -> str:
            try:
                resposta = self._client.models.generate_content(
                    model=modelo, contents=prompt, config=config,
                )
            except (genai_errors.ClientError, genai_errors.ServerError) as exc:
                if not _retryable_exception(exc):
                    raise GeracaoConteudoError(
                        f"Erro não recuperável da API Gemini ({modelo}): {exc}"
                    ) from exc
                raise
            texto = resposta.text
            if not texto:
                raise genai_errors.ServerError(
                    503, {"error": {"message": "Resposta vazia do modelo"}}
                )
            return texto

        return _executar()

    def gerar_conteudo_apostila(self, item: ItemCurricular) -> ConteudoApostilaGerado:
        """Gera e valida o conteúdo textual completo de uma apostila.

        Tenta primeiro o modelo principal; em caso de esgotamento de quota
        diária (RPD) reportado pela própria API, tenta automaticamente o
        modelo de reserva configurado."""
        prompt = construir_prompt_apostila(item)
        modelos_a_tentar = [self._settings.gemini_model]
        if self._settings.gemini_fallback_model != self._settings.gemini_model:
            modelos_a_tentar.append(self._settings.gemini_fallback_model)

        ultimo_erro: Optional[Exception] = None
        for modelo in modelos_a_tentar:
            try:
                texto_json = self._chamar_modelo(modelo, prompt)
                conteudo = self._validar_resposta(texto_json, item)
                logger.info(
                    "Conteúdo gerado com sucesso para %s usando modelo %s (%d palavras).",
                    item.codigo, modelo, conteudo.contagem_palavras(),
                )
                return conteudo
            except LimiteDiarioExcedidoError:
                raise
            except (genai_errors.ClientError, genai_errors.ServerError, GeracaoConteudoError) as exc:
                logger.error("Falha ao gerar conteúdo com modelo %s para %s: %s", modelo, item.codigo, exc)
                ultimo_erro = exc
                continue
            except ConteudoInsuficienteError as exc:
                logger.warning(
                    "Conteúdo insuficiente do modelo %s para %s: %s. Tentando próximo modelo.",
                    modelo, item.codigo, exc,
                )
                ultimo_erro = exc
                continue

        raise GeracaoConteudoError(
            f"Não foi possível gerar conteúdo válido para {item.codigo} "
            f"({item.titulo}) após tentar todos os modelos configurados. "
            f"Último erro: {ultimo_erro}"
        )

    def _validar_resposta(self, texto_json: str, item: ItemCurricular) -> ConteudoApostilaGerado:
        try:
            bruto = json.loads(texto_json)
        except json.JSONDecodeError as exc:
            raise GeracaoConteudoError(
                f"Resposta do Gemini não é um JSON válido para {item.codigo}: {exc}"
            ) from exc

        try:
            conteudo = ConteudoApostilaGerado.model_validate(bruto)
        except Exception as exc:  # noqa: BLE001 — validação ampla de schema externo
            raise GeracaoConteudoError(
                f"Resposta do Gemini não corresponde ao esquema esperado para {item.codigo}: {exc}"
            ) from exc

        palavras = conteudo.contagem_palavras()
        if palavras < _PALAVRAS_MINIMAS:
            raise ConteudoInsuficienteError(
                f"Conteúdo gerado para {item.codigo} tem apenas {palavras} palavras "
                f"(mínimo exigido: {_PALAVRAS_MINIMAS})."
            )
        return conteudo
