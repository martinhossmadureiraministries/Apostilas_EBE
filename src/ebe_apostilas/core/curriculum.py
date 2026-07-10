"""
Carregamento e validação do mapa curricular oficial da EBE.

O mapa curricular (``data/curriculo_apostilas.json``) foi extraído de forma
integral e fiel do documento institucional ``EBE_Mapa_Completo_Apostilas-2.pdf``
(código EBE-PLAN-APO) e contém exactamente as 1.029 apostilas oficiais,
organizadas por Nível → Instituto → Escola → Curso → Módulo.

Este módulo **nunca** gera, altera ou reordena títulos: apenas lê e valida a
integridade do currículo, servindo de fonte única de verdade (single source
of truth) para todo o sistema de geração.
"""
from __future__ import annotations

import json
from pathlib import Path

from ebe_apostilas.core.models import ItemCurricular

TOTAL_APOSTILAS_OFICIAL = 1029


class CurriculoInvalidoError(Exception):
    """Lançado quando o mapa curricular não corresponde à especificação
    oficial (contagem, IDs em falta, duplicados ou títulos alterados)."""


class Curriculo:
    """Representa o mapa curricular completo, imutável, carregado em
    memória e indexado por ID para acesso rápido."""

    def __init__(self, itens: list[ItemCurricular]):
        self._itens: dict[int, ItemCurricular] = {item.id: item for item in itens}
        self._validar_integridade()

    def _validar_integridade(self) -> None:
        ids = sorted(self._itens.keys())
        esperado = list(range(1, TOTAL_APOSTILAS_OFICIAL + 1))
        if ids != esperado:
            faltantes = sorted(set(esperado) - set(ids))
            excedentes = sorted(set(ids) - set(esperado))
            raise CurriculoInvalidoError(
                "O mapa curricular não corresponde às 1.029 apostilas oficiais. "
                f"IDs em falta: {faltantes[:20]}{'...' if len(faltantes) > 20 else ''}. "
                f"IDs inesperados: {excedentes[:20]}{'...' if len(excedentes) > 20 else ''}."
            )

    def __len__(self) -> int:
        return len(self._itens)

    def obter(self, apostila_id: int) -> ItemCurricular:
        try:
            return self._itens[apostila_id]
        except KeyError as exc:
            raise KeyError(
                f"Apostila {apostila_id} não existe no mapa curricular oficial "
                f"(intervalo válido: 1-{TOTAL_APOSTILAS_OFICIAL})."
            ) from exc

    def existe(self, apostila_id: int) -> bool:
        return apostila_id in self._itens

    def todos_ids(self) -> list[int]:
        return sorted(self._itens.keys())

    def itens_em_ordem(self) -> list[ItemCurricular]:
        return [self._itens[i] for i in self.todos_ids()]

    def proximo_pendente(self, ids_concluidos: set[int]) -> ItemCurricular | None:
        """Devolve a próxima apostila (em ordem curricular) ainda não
        concluída, respeitando estritamente a ordem oficial do mapa."""
        for apostila_id in self.todos_ids():
            if apostila_id not in ids_concluidos:
                return self._itens[apostila_id]
        return None

    def proximos_pendentes(self, ids_concluidos: set[int], quantidade: int) -> list[ItemCurricular]:
        """Devolve até ``quantidade`` apostilas pendentes, em ordem
        curricular, ignorando as já concluídas."""
        resultado: list[ItemCurricular] = []
        for apostila_id in self.todos_ids():
            if len(resultado) >= quantidade:
                break
            if apostila_id not in ids_concluidos:
                resultado.append(self._itens[apostila_id])
        return resultado


def carregar_curriculo(caminho: Path) -> Curriculo:
    """Carrega e valida o mapa curricular oficial a partir do JSON fonte."""
    if not caminho.exists():
        raise FileNotFoundError(
            f"Mapa curricular não encontrado em {caminho}. "
            "Este ficheiro é obrigatório e não deve ser removido nem "
            "regenerado automaticamente sem revisão institucional."
        )
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    itens = [ItemCurricular.model_validate(item) for item in bruto]
    return Curriculo(itens)
