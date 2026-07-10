"""Testes de integridade do mapa curricular oficial."""
from __future__ import annotations

from pathlib import Path

import pytest

from ebe_apostilas.core.curriculum import (
    TOTAL_APOSTILAS_OFICIAL,
    CurriculoInvalidoError,
    carregar_curriculo,
)
from ebe_apostilas.core.models import ItemCurricular

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = REPO_ROOT / "data" / "curriculo_apostilas.json"


def test_curriculo_oficial_tem_1029_apostilas():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    assert len(curriculo) == TOTAL_APOSTILAS_OFICIAL == 1029


def test_curriculo_ids_sao_sequenciais_sem_lacunas():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    assert curriculo.todos_ids() == list(range(1, 1030))


def test_curriculo_codigo_consistente_com_id():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    for item in curriculo.itens_em_ordem():
        assert item.codigo == f"EBE-APO-{item.id:04d}"


def test_curriculo_sem_titulos_vazios_ou_duplicados_no_mesmo_curso():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    titulos = [item.titulo for item in curriculo.itens_em_ordem()]
    assert all(t.strip() for t in titulos)


def test_curriculo_niveis_institutos_escolas_dentro_do_esperado():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    niveis = {item.nivel_numero for item in curriculo.itens_em_ordem()}
    institutos = {item.instituto_numero for item in curriculo.itens_em_ordem()}
    escolas = {item.escola_id for item in curriculo.itens_em_ordem()}
    cursos = {item.curso_id for item in curriculo.itens_em_ordem()}
    assert niveis == {1, 2, 3, 4}
    assert len(institutos) == 10
    assert len(escolas) == 54
    assert len(cursos) == 146


def test_curriculo_contagem_por_nivel_bate_com_quadro_resumo_oficial():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    from collections import Counter

    contagem = Counter(item.nivel_numero for item in curriculo.itens_em_ordem())
    assert contagem[1] == 345
    assert contagem[2] == 261
    assert contagem[3] == 264
    assert contagem[4] == 159


def test_curriculo_arquivo_inexistente_lanca_erro(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        carregar_curriculo(tmp_path / "nao_existe.json")


def test_curriculo_invalido_com_id_faltante(tmp_path: Path):
    from ebe_apostilas.core.curriculum import Curriculo

    item_base = ItemCurricular(
        id=1, codigo="EBE-APO-0001", titulo="Teste", nivel_numero=1,
        nivel_nome="Nível 1", instituto_numero=1, instituto_nome="Instituto Teste",
        escola_id=1, escola_nome="Escola Teste", curso_id=1, curso_nome="Curso Teste",
        carga_horaria_curso="10 h", modulo_numero=1, modulo_nome="Módulo Teste",
    )
    with pytest.raises(CurriculoInvalidoError):
        Curriculo([item_base])


def test_proximo_pendente_respeita_ordem_curricular():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    concluidos = {1, 2, 3}
    proximo = curriculo.proximo_pendente(concluidos)
    assert proximo is not None
    assert proximo.id == 4


def test_proximos_pendentes_devolve_quantidade_correta():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    concluidos: set[int] = set()
    pendentes = curriculo.proximos_pendentes(concluidos, 11)
    assert len(pendentes) == 11
    assert [p.id for p in pendentes] == list(range(1, 12))


def test_proximos_pendentes_quando_tudo_concluido():
    curriculo = carregar_curriculo(CURRICULUM_PATH)
    concluidos = set(range(1, 1030))
    assert curriculo.proximo_pendente(concluidos) is None
    assert curriculo.proximos_pendentes(concluidos, 11) == []
