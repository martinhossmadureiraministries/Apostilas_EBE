"""
Configuração central de logging da plataforma.

Produz logs simultaneamente em consola (para acompanhamento em tempo real,
incluindo GitHub Actions) e em ficheiro rotativo persistente em
``logs/execucao_YYYY-MM-DD.log``, facilitando auditoria e diagnóstico de
falhas em execuções automáticas e não supervisionadas.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_CONFIGURED = False


class _SemSegredoFilter(logging.Filter):
    """Filtro de segurança: impede que qualquer valor parecido com uma
    chave de API (>20 caracteres alfanuméricos contíguos) seja escrito em
    log, mesmo por engano em código futuro."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "AIza" in msg or "api_key=" in msg.lower():
            record.msg = "[MENSAGEM OMITIDA — possível segredo detectado no log]"
            record.args = ()
        return True


def configurar_logging(logs_dir: Path, nivel: int = logging.INFO) -> logging.Logger:
    """Configura (uma única vez por processo) o logger raiz da aplicação."""
    global _CONFIGURED
    logger = logging.getLogger("ebe_apostilas")
    if _CONFIGURED:
        return logger

    logs_dir.mkdir(parents=True, exist_ok=True)
    data_hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = logs_dir / f"execucao_{data_hoje}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_SemSegredoFilter())

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_SemSegredoFilter())

    logger.setLevel(nivel)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    _CONFIGURED = True
    logger.info("Logging configurado. Ficheiro de log: %s", log_path)
    return logger


def get_logger(nome: str) -> logging.Logger:
    """Devolve um logger filho, herdando a configuração do logger raiz da
    aplicação (deve ser chamado após ``configurar_logging``)."""
    return logging.getLogger(f"ebe_apostilas.{nome}")
