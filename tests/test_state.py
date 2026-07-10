"""Testes do gestor de checkpoint/estado e do PROJECT_STATE.md."""
from __future__ import annotations

from pathlib import Path

from ebe_apostilas.core.state import GestorEstado


def test_estado_inicial_sem_ficheiro(tmp_path: Path):
    gestor = GestorEstado(tmp_path / "estado.json", tmp_path / "PROJECT_STATE.md")
    assert gestor.estado.total_concluidas == 0
    assert gestor.estado.status_ultima_execucao == "nunca_executado"


def test_estado_persiste_e_recarrega(tmp_path: Path):
    caminho_estado = tmp_path / "estado.json"
    caminho_md = tmp_path / "PROJECT_STATE.md"

    gestor = GestorEstado(caminho_estado, caminho_md)
    gestor.iniciar_execucao("workflow-teste")
    gestor.registar_conclusao_apostila(1, "EBE-APO-0001", "Título Teste")
    gestor.atualizar_progresso(1, 2, "EBE-APO-0002", "Próxima")
    gestor.finalizar_execucao("concluido")

    assert caminho_estado.exists()
    assert caminho_md.exists()

    gestor2 = GestorEstado(caminho_estado, caminho_md)
    assert gestor2.estado.total_concluidas == 1
    assert gestor2.estado.ultima_apostila_concluida_codigo == "EBE-APO-0001"
    assert gestor2.estado.proxima_apostila_codigo == "EBE-APO-0002"
    assert gestor2.estado.status_ultima_execucao == "concluido"


def test_project_state_md_contem_campos_obrigatorios(tmp_path: Path):
    caminho_estado = tmp_path / "estado.json"
    caminho_md = tmp_path / "PROJECT_STATE.md"
    gestor = GestorEstado(caminho_estado, caminho_md)
    gestor.iniciar_execucao("workflow-diario")
    gestor.registar_conclusao_apostila(5, "EBE-APO-0005", "Apostila Cinco")
    gestor.atualizar_progresso(5, 6, "EBE-APO-0006", "Apostila Seis")
    gestor.finalizar_execucao("concluido")

    conteudo = caminho_md.read_text(encoding="utf-8")
    assert "EBE-APO-0005" in conteudo
    assert "EBE-APO-0006" in conteudo
    assert "workflow-diario" in conteudo
    assert "5 / 1029" in conteudo or "**5" in conteudo


def test_estado_regista_erros_da_execucao_atual(tmp_path: Path):
    gestor = GestorEstado(tmp_path / "estado.json", tmp_path / "PROJECT_STATE.md")
    gestor.iniciar_execucao("workflow-teste")
    gestor.registar_erro_apostila(10, "EBE-APO-0010", "Erro simulado de teste")
    assert len(gestor.estado.erros_execucao_atual) == 1
    assert gestor.estado.erros_execucao_atual[0].codigo == "EBE-APO-0010"


def test_estado_reinicia_erros_a_cada_nova_execucao(tmp_path: Path):
    gestor = GestorEstado(tmp_path / "estado.json", tmp_path / "PROJECT_STATE.md")
    gestor.iniciar_execucao("exec-1")
    gestor.registar_erro_apostila(1, "EBE-APO-0001", "Erro 1")
    assert len(gestor.estado.erros_execucao_atual) == 1

    gestor.iniciar_execucao("exec-2")
    assert len(gestor.estado.erros_execucao_atual) == 0
