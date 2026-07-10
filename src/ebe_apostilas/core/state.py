"""
Checkpoint e retomada automática da execução.

Mantém, em ``data/estado_producao.json``, um retrato do estado corrente da
produção (última apostila concluída, próxima apostila, progresso, contagem
de erros da execução corrente etc.), permitindo que qualquer execução —
manual ou via GitHub Actions — retome exactamente do ponto em que a
anterior parou, mesmo após falhas ou interrupções.

Este módulo também é responsável por (re)gerar o ficheiro ``PROJECT_STATE.md``
na raiz do repositório, com a informação exigida: última apostila concluída,
próxima apostila, progresso, data, versão, estado e erros.
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from ebe_apostilas import __version__ as VERSAO_PLATAFORMA
from ebe_apostilas.core.curriculum import TOTAL_APOSTILAS_OFICIAL


class ErroExecucao(BaseModel):
    apostila_id: int
    codigo: str
    mensagem: str
    data: str


class EstadoProducao(BaseModel):
    """Estado persistente da produção, actualizado a cada execução."""

    ultima_apostila_concluida_id: Optional[int] = None
    ultima_apostila_concluida_codigo: Optional[str] = None
    ultima_apostila_concluida_titulo: Optional[str] = None
    proxima_apostila_id: Optional[int] = None
    proxima_apostila_codigo: Optional[str] = None
    proxima_apostila_titulo: Optional[str] = None
    total_concluidas: int = 0
    total_oficial: int = TOTAL_APOSTILAS_OFICIAL
    percentual_concluido: float = 0.0
    data_ultima_execucao: Optional[str] = None
    status_ultima_execucao: str = "nunca_executado"
    workflow_executado: Optional[str] = None
    versao_plataforma: str = VERSAO_PLATAFORMA
    erros_execucao_atual: list[ErroExecucao] = Field(default_factory=list)
    apostilas_geradas_na_execucao_atual: list[str] = Field(default_factory=list)


class GestorEstado:
    """Carrega, actualiza e persiste o ``EstadoProducao`` e sincroniza o
    ficheiro humano-legível ``PROJECT_STATE.md``."""

    def __init__(self, caminho_estado: Path, caminho_project_state_md: Path):
        self._caminho_estado = caminho_estado
        self._caminho_md = caminho_project_state_md
        self.estado = self._carregar()

    def _carregar(self) -> EstadoProducao:
        if not self._caminho_estado.exists():
            return EstadoProducao()
        try:
            bruto = json.loads(self._caminho_estado.read_text(encoding="utf-8"))
            return EstadoProducao.model_validate(bruto)
        except (json.JSONDecodeError, ValueError):
            return EstadoProducao()

    def persistir(self) -> None:
        self._caminho_estado.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._caminho_estado.with_suffix(".json.tmp")
        tmp.write_text(
            self.estado.model_dump_json(indent=2), encoding="utf-8"
        )
        tmp.replace(self._caminho_estado)

    def iniciar_execucao(self, workflow: str) -> None:
        self.estado.workflow_executado = workflow
        self.estado.data_ultima_execucao = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.estado.status_ultima_execucao = "em_execucao"
        self.estado.erros_execucao_atual = []
        self.estado.apostilas_geradas_na_execucao_atual = []
        self.persistir()

    def registar_conclusao_apostila(self, apostila_id: int, codigo: str, titulo: str) -> None:
        self.estado.ultima_apostila_concluida_id = apostila_id
        self.estado.ultima_apostila_concluida_codigo = codigo
        self.estado.ultima_apostila_concluida_titulo = titulo
        self.estado.apostilas_geradas_na_execucao_atual.append(f"{codigo} — {titulo}")
        self.persistir()

    def registar_erro_apostila(self, apostila_id: int, codigo: str, mensagem: str) -> None:
        self.estado.erros_execucao_atual.append(
            ErroExecucao(
                apostila_id=apostila_id,
                codigo=codigo,
                mensagem=mensagem[:500],
                data=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        )
        self.persistir()

    def atualizar_progresso(
        self,
        total_concluidas: int,
        proxima_id: Optional[int],
        proxima_codigo: Optional[str],
        proxima_titulo: Optional[str],
    ) -> None:
        self.estado.total_concluidas = total_concluidas
        self.estado.percentual_concluido = round(
            (total_concluidas / TOTAL_APOSTILAS_OFICIAL) * 100, 2
        )
        self.estado.proxima_apostila_id = proxima_id
        self.estado.proxima_apostila_codigo = proxima_codigo
        self.estado.proxima_apostila_titulo = proxima_titulo
        self.persistir()

    def finalizar_execucao(self, status: str) -> None:
        self.estado.status_ultima_execucao = status
        self.estado.data_ultima_execucao = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.persistir()
        self.escrever_project_state_md()

    def escrever_project_state_md(self) -> None:
        e = self.estado
        barra_len = 30
        preenchido = int(barra_len * (e.percentual_concluido / 100))
        barra = "█" * preenchido + "░" * (barra_len - preenchido)

        linhas_erros = (
            "\n".join(
                f"- `{err.codigo}` (ID {err.apostila_id}) — {err.mensagem} _( {err.data} )_"
                for err in e.erros_execucao_atual
            )
            if e.erros_execucao_atual
            else "_Nenhum erro registado na última execução._"
        )

        linhas_geradas = (
            "\n".join(f"- {item}" for item in e.apostilas_geradas_na_execucao_atual)
            if e.apostilas_geradas_na_execucao_atual
            else "_Nenhuma apostila gerada na última execução._"
        )

        conteudo = f"""# PROJECT_STATE — Estado da Produção de Apostilas EBE

> Ficheiro gerado e actualizado automaticamente pela plataforma
> `ebe_apostilas`. Não editar manualmente — as alterações serão
> substituídas na próxima execução.

## Resumo Geral

| Campo | Valor |
|---|---|
| Versão da plataforma | `{e.versao_plataforma}` |
| Sistema | `{platform.system()} {platform.release()}` |
| Última execução (UTC) | `{e.data_ultima_execucao or "—"}` |
| Estado da última execução | **{e.status_ultima_execucao}** |
| Workflow executado | `{e.workflow_executado or "—"}` |
| Total concluído | **{e.total_concluidas} / {e.total_oficial}** |
| Progresso | `{barra}` **{e.percentual_concluido}%** |

## Última Apostila Concluída

- **ID:** {e.ultima_apostila_concluida_id or "—"}
- **Código:** `{e.ultima_apostila_concluida_codigo or "—"}`
- **Título:** {e.ultima_apostila_concluida_titulo or "—"}

## Próxima Apostila a Gerar

- **ID:** {e.proxima_apostila_id if e.proxima_apostila_id is not None else "—"}
- **Código:** `{e.proxima_apostila_codigo or "—"}`
- **Título:** {e.proxima_apostila_titulo or "—"}

## Apostilas Geradas na Última Execução

{linhas_geradas}

## Erros da Última Execução

{linhas_erros}

## Retomada Automática

O sistema retoma sempre a partir da apostila pendente mais antiga segundo a
ordem oficial do mapa curricular (`data/curriculo_apostilas.json`),
consultando o registo de duplicidade (`data/registro_apostilas.json`) para
nunca reprocessar apostilas já concluídas. Não é necessária qualquer acção
manual para continuar a produção — basta reexecutar o workflow ou o comando
`ebe-apostilas gerar-lote`.

---
_Actualizado automaticamente em {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC._
"""
        self._caminho_md.write_text(conteudo, encoding="utf-8")
