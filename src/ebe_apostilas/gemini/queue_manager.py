"""
Fila de processamento sequencial das apostilas pendentes.

Processa as apostilas em ordem curricular estrita, respeitando os limites
da API (via ``RateLimiter``) e persistindo o progresso a cada apostila
concluída — permitindo interromper e retomar a qualquer momento sem perda
de trabalho e sem duplicação.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ebe_apostilas.core.curriculum import Curriculo
from ebe_apostilas.core.models import ItemCurricular
from ebe_apostilas.core.registry import RegistroDuplicidade
from ebe_apostilas.core.state import GestorEstado
from ebe_apostilas.docx_gen.builder import ApostilaDocxBuilder
from ebe_apostilas.gemini.client import GeminiClient, GeracaoConteudoError
from ebe_apostilas.gemini.rate_limiter import LimiteDiarioExcedidoError

logger = logging.getLogger("ebe_apostilas.queue_manager")


@dataclass
class ResultadoLote:
    """Resumo de uma execução em lote da fila de processamento."""

    processadas_com_sucesso: list[str] = field(default_factory=list)
    falhadas: list[str] = field(default_factory=list)
    interrompido_por_limite_diario: bool = False


class FilaProcessamentoApostilas:
    """Orquestra a geração sequencial de apostilas pendentes: consulta o
    currículo e o registo de duplicidade, invoca o cliente Gemini, gera o
    DOCX e regista o resultado (sucesso ou erro), actualizando sempre o
    estado de checkpoint."""

    def __init__(
        self,
        curriculo: Curriculo,
        registro: RegistroDuplicidade,
        estado: GestorEstado,
        gemini_client: GeminiClient,
        docx_builder: ApostilaDocxBuilder,
    ):
        self._curriculo = curriculo
        self._registro = registro
        self._estado = estado
        self._gemini_client = gemini_client
        self._docx_builder = docx_builder

    def _atualizar_progresso_estado(self) -> None:
        concluidos = self._registro.ids_concluidos()
        proximo = self._curriculo.proximo_pendente(concluidos)
        self._estado.atualizar_progresso(
            total_concluidas=len(concluidos),
            proxima_id=proximo.id if proximo else None,
            proxima_codigo=proximo.codigo if proximo else None,
            proxima_titulo=proximo.titulo if proximo else None,
        )

    def processar_uma(self, item: ItemCurricular) -> bool:
        """Processa uma única apostila. Devolve ``True`` em caso de
        sucesso. Nunca lança excepção de negócio — erros são registados e
        reportados através do valor de retorno, excepto
        ``LimiteDiarioExcedidoError``, que é propagada para interromper o
        lote imediatamente."""
        if self._registro.esta_concluida(item.id):
            logger.info("Apostila %s já concluída — a saltar (controlo de duplicidade).", item.codigo)
            return True

        logger.info("Iniciando processamento de %s — %s", item.codigo, item.titulo)
        try:
            conteudo = self._gemini_client.gerar_conteudo_apostila(item)
            caminho_docx = self._docx_builder.construir(item, conteudo)
            texto_completo_para_hash = conteudo.model_dump_json()
            self._registro.registar_sucesso(
                apostila_id=item.id,
                codigo=item.codigo,
                titulo=item.titulo,
                conteudo_texto=texto_completo_para_hash,
                caminho_docx=str(caminho_docx),
                palavras=conteudo.contagem_palavras(),
                modelo_usado=self._gemini_client.settings.gemini_model,
            )
            self._estado.registar_conclusao_apostila(item.id, item.codigo, item.titulo)
            self._atualizar_progresso_estado()
            logger.info("Apostila %s concluída com sucesso: %s", item.codigo, caminho_docx)
            return True
        except LimiteDiarioExcedidoError:
            raise
        except GeracaoConteudoError as exc:
            logger.error("Falha definitiva ao gerar %s: %s", item.codigo, exc)
            self._registro.registar_erro(item.id, item.codigo, item.titulo, str(exc))
            self._estado.registar_erro_apostila(item.id, item.codigo, str(exc))
            return False
        except Exception as exc:  # noqa: BLE001 — isolamento de falhas por item
            logger.exception("Erro inesperado ao processar %s", item.codigo)
            self._registro.registar_erro(item.id, item.codigo, item.titulo, str(exc))
            self._estado.registar_erro_apostila(item.id, item.codigo, str(exc))
            return False

    def processar_lote(self, quantidade: int) -> ResultadoLote:
        """Processa até ``quantidade`` apostilas pendentes, em ordem
        curricular, parando antecipadamente se a quota diária da API se
        esgotar (retomada automática na próxima execução)."""
        resultado = ResultadoLote()
        concluidos = self._registro.ids_concluidos()
        pendentes = self._curriculo.proximos_pendentes(concluidos, quantidade)

        if not pendentes:
            logger.info("Não há apostilas pendentes — currículo 100%% concluído (%d/%d).", len(concluidos), len(self._curriculo))
            self._atualizar_progresso_estado()
            return resultado

        logger.info("Lote de processamento: %d apostilas pendentes seleccionadas.", len(pendentes))

        for item in pendentes:
            try:
                sucesso = self.processar_uma(item)
            except LimiteDiarioExcedidoError as exc:
                logger.warning(
                    "Limite diário da API Gemini atingido: %s. Encerrando lote "
                    "correctamente — a execução será retomada automaticamente "
                    "na próxima chamada do workflow.",
                    exc,
                )
                resultado.interrompido_por_limite_diario = True
                break

            if sucesso:
                resultado.processadas_com_sucesso.append(item.codigo)
            else:
                resultado.falhadas.append(item.codigo)

        self._atualizar_progresso_estado()
        return resultado
