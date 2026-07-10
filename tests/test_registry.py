"""Testes do registo de controlo de duplicidade."""
from __future__ import annotations

from pathlib import Path

from ebe_apostilas.core.models import StatusApostila
from ebe_apostilas.core.registry import RegistroDuplicidade


def test_registro_inicia_vazio(tmp_path: Path):
    registro = RegistroDuplicidade(tmp_path / "registro.json")
    assert registro.ids_concluidos() == set()
    assert registro.total_concluidas() == 0


def test_registro_sucesso_persiste_e_recarrega(tmp_path: Path):
    caminho = tmp_path / "registro.json"
    registro = RegistroDuplicidade(caminho)
    registro.registar_sucesso(
        apostila_id=1, codigo="EBE-APO-0001", titulo="Teste",
        conteudo_texto="conteudo", caminho_docx="/tmp/x.docx",
        palavras=1000, modelo_usado="gemini-2.5-flash",
    )
    assert registro.esta_concluida(1)
    assert caminho.exists()

    registro2 = RegistroDuplicidade(caminho)
    assert registro2.esta_concluida(1)
    assert registro2.total_concluidas() == 1


def test_registro_nao_reprocessa_apostila_concluida(tmp_path: Path):
    registro = RegistroDuplicidade(tmp_path / "registro.json")
    registro.registar_sucesso(
        apostila_id=5, codigo="EBE-APO-0005", titulo="Teste 5",
        conteudo_texto="c", caminho_docx="/tmp/x.docx", palavras=1000,
        modelo_usado="gemini-2.5-flash",
    )
    assert 5 in registro.ids_concluidos()
    assert 6 not in registro.ids_concluidos()


def test_registro_erro_nao_marca_como_concluida(tmp_path: Path):
    registro = RegistroDuplicidade(tmp_path / "registro.json")
    registro.registar_erro(2, "EBE-APO-0002", "Teste 2", "Erro simulado")
    assert not registro.esta_concluida(2)
    registro_obj = registro.obter(2)
    assert registro_obj is not None
    assert registro_obj.status == StatusApostila.ERRO
    assert registro_obj.ultimo_erro == "Erro simulado"


def test_registro_versao_incrementa_apos_erro_e_sucesso(tmp_path: Path):
    registro = RegistroDuplicidade(tmp_path / "registro.json")
    registro.registar_erro(3, "EBE-APO-0003", "Teste 3", "Falha 1")
    registro.registar_sucesso(
        apostila_id=3, codigo="EBE-APO-0003", titulo="Teste 3",
        conteudo_texto="c", caminho_docx="/tmp/x.docx", palavras=1000,
        modelo_usado="gemini-2.5-flash",
    )
    registro_final = registro.obter(3)
    assert registro_final is not None
    assert registro_final.status == StatusApostila.CONCLUIDA
    assert registro_final.tentativas == 2


def test_registro_corrompido_nao_quebra_carregamento(tmp_path: Path):
    caminho = tmp_path / "registro.json"
    caminho.write_text("{ json invalido ][", encoding="utf-8")
    registro = RegistroDuplicidade(caminho)
    assert registro.ids_concluidos() == set()
