"""Testes dos modelos de dados (Pydantic)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ebe_apostilas.core.models import (
    ConteudoApostilaGerado,
    ItemCurricular,
    RegistroApostila,
    StatusApostila,
)


def test_item_curricular_valida_codigo_consistente():
    with pytest.raises(ValidationError):
        ItemCurricular(
            id=1, codigo="EBE-APO-9999", titulo="Teste", nivel_numero=1,
            nivel_nome="Nível 1", instituto_numero=1, instituto_nome="Instituto",
            escola_id=1, escola_nome="Escola", curso_id=1, curso_nome="Curso",
            carga_horaria_curso="10 h", modulo_numero=1, modulo_nome="Módulo",
        )


def test_item_curricular_id_fora_do_intervalo():
    with pytest.raises(ValidationError):
        ItemCurricular(
            id=1030, codigo="EBE-APO-1030", titulo="Teste", nivel_numero=1,
            nivel_nome="Nível 1", instituto_numero=1, instituto_nome="Instituto",
            escola_id=1, escola_nome="Escola", curso_id=1, curso_nome="Curso",
            carga_horaria_curso="10 h", modulo_numero=1, modulo_nome="Módulo",
        )


def test_conteudo_apostila_contagem_palavras(conteudo_exemplo: ConteudoApostilaGerado):
    assert conteudo_exemplo.contagem_palavras() > 50


def test_registro_apostila_calcular_hash_deterministico():
    h1 = RegistroApostila.calcular_hash("texto identico")
    h2 = RegistroApostila.calcular_hash("texto identico")
    h3 = RegistroApostila.calcular_hash("texto diferente")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex digest


def test_registro_apostila_status_enum():
    registro = RegistroApostila(
        id=1, codigo="EBE-APO-0001", titulo="Teste",
        hash_conteudo="abc", versao=1, data_conclusao="2026-01-01T00:00:00+00:00",
        status=StatusApostila.CONCLUIDA,
    )
    assert registro.status == StatusApostila.CONCLUIDA
    assert registro.status.value == "concluida"
