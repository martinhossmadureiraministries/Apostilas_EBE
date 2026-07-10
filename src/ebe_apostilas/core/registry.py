"""
Registo de duplicidade — impede que uma apostila já concluída seja gerada
novamente.

Persistido em ``data/registro_apostilas.json``, este registo mantém, para
cada apostila processada: ID, título, hash SHA-256 do conteúdo gerado,
versão, data de conclusão e estado. É a fonte de verdade usada pelo motor
de execução para decidir quais apostilas ainda precisam de ser produzidas.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock

from ebe_apostilas.core.models import RegistroApostila, StatusApostila

logger = logging.getLogger("ebe_apostilas.registry")


class RegistroDuplicidade:
    """Gestor thread-safe do registo de apostilas já processadas."""

    def __init__(self, caminho: Path):
        self._caminho = caminho
        self._lock = Lock()
        self._registros: dict[int, RegistroApostila] = {}
        self._carregar()

    def _carregar(self) -> None:
        if not self._caminho.exists():
            self._registros = {}
            return
        try:
            bruto = json.loads(self._caminho.read_text(encoding="utf-8"))
            self._registros = {
                int(item["id"]): RegistroApostila.model_validate(item) for item in bruto
            }
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error(
                "Registo de duplicidade corrompido em %s (%s). "
                "Iniciando registo vazio para evitar perda total — "
                "recomenda-se restaurar a partir do histórico Git.",
                self._caminho,
                exc,
            )
            self._registros = {}

    def _persistir(self) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._caminho.with_suffix(".json.tmp")
        dados = [r.model_dump(mode="json") for r in self._ordenados()]
        tmp_path.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp_path.replace(self._caminho)  # escrita atómica

    def _ordenados(self) -> list[RegistroApostila]:
        return [self._registros[i] for i in sorted(self._registros.keys())]

    def esta_concluida(self, apostila_id: int) -> bool:
        with self._lock:
            registro = self._registros.get(apostila_id)
            return registro is not None and registro.status == StatusApostila.CONCLUIDA

    def ids_concluidos(self) -> set[int]:
        with self._lock:
            return {
                i for i, r in self._registros.items() if r.status == StatusApostila.CONCLUIDA
            }

    def obter(self, apostila_id: int) -> RegistroApostila | None:
        with self._lock:
            return self._registros.get(apostila_id)

    def registar_sucesso(
        self,
        apostila_id: int,
        codigo: str,
        titulo: str,
        conteudo_texto: str,
        caminho_docx: str,
        palavras: int,
        modelo_usado: str,
    ) -> RegistroApostila:
        """Regista a conclusão bem-sucedida de uma apostila. Se já existir
        um registo anterior (por exemplo, de uma tentativa com erro),
        incrementa a versão."""
        with self._lock:
            anterior = self._registros.get(apostila_id)
            versao = (anterior.versao + 1) if anterior else 1
            registro = RegistroApostila(
                id=apostila_id,
                codigo=codigo,
                titulo=titulo,
                hash_conteudo=RegistroApostila.calcular_hash(conteudo_texto),
                versao=versao,
                data_conclusao=RegistroApostila.agora_iso(),
                status=StatusApostila.CONCLUIDA,
                caminho_docx=caminho_docx,
                tentativas=(anterior.tentativas if anterior else 0) + 1,
                ultimo_erro=None,
                palavras=palavras,
                modelo_usado=modelo_usado,
            )
            self._registros[apostila_id] = registro
            self._persistir()
            logger.info("Registada conclusão: %s (%s) — v%d", codigo, titulo, versao)
            return registro

    def registar_erro(self, apostila_id: int, codigo: str, titulo: str, erro: str) -> None:
        with self._lock:
            anterior = self._registros.get(apostila_id)
            registro = RegistroApostila(
                id=apostila_id,
                codigo=codigo,
                titulo=titulo,
                hash_conteudo=anterior.hash_conteudo if anterior else "",
                versao=anterior.versao if anterior else 0,
                data_conclusao=anterior.data_conclusao if anterior else "",
                status=StatusApostila.ERRO,
                caminho_docx=anterior.caminho_docx if anterior else None,
                tentativas=(anterior.tentativas if anterior else 0) + 1,
                ultimo_erro=erro[:2000],
                palavras=anterior.palavras if anterior else 0,
                modelo_usado=anterior.modelo_usado if anterior else None,
            )
            self._registros[apostila_id] = registro
            self._persistir()
            logger.warning("Registado erro: %s (%s) — %s", codigo, titulo, erro[:200])

    def total_concluidas(self) -> int:
        with self._lock:
            return sum(1 for r in self._registros.values() if r.status == StatusApostila.CONCLUIDA)

    def todos(self) -> list[RegistroApostila]:
        with self._lock:
            return self._ordenados()
