"""
Interface de linha de comando (CLI) da plataforma ``ebe_apostilas``.

Comandos disponíveis:

- ``ebe-apostilas gerar-lote``       — gera o próximo lote de apostilas
  pendentes (usado pelo workflow diário do GitHub Actions e localmente).
- ``ebe-apostilas status``           — mostra o progresso actual da produção.
- ``ebe-apostilas validar-curriculo``— valida a integridade do mapa
  curricular oficial (1.029 apostilas, sem duplicados nem lacunas).
- ``ebe-apostilas validar-ambiente`` — valida variáveis de ambiente
  obrigatórias antes de uma execução real.

Uso local::

    python -m ebe_apostilas.cli.main gerar-lote --quantidade 11
"""
from __future__ import annotations

import argparse
import logging
import sys

from ebe_apostilas import __version__
from ebe_apostilas.core.config import Settings, get_settings, mask_secret
from ebe_apostilas.core.curriculum import CurriculoInvalidoError, carregar_curriculo
from ebe_apostilas.core.logging_config import configurar_logging, get_logger
from ebe_apostilas.core.registry import RegistroDuplicidade
from ebe_apostilas.core.state import GestorEstado
from ebe_apostilas.docx_gen.builder import ApostilaDocxBuilder
from ebe_apostilas.gemini.client import GeminiClient
from ebe_apostilas.gemini.queue_manager import FilaProcessamentoApostilas
from ebe_apostilas.gemini.rate_limiter import RateLimiter


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ebe-apostilas",
        description="Plataforma automática de geração das apostilas curriculares da EBE via Gemini.",
    )
    parser.add_argument("--version", action="version", version=f"ebe-apostilas {__version__}")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_gerar = subparsers.add_parser("gerar-lote", help="Gera o próximo lote de apostilas pendentes.")
    p_gerar.add_argument(
        "--quantidade", type=int, default=None,
        help="Número de apostilas a gerar nesta execução (padrão: valor de APOSTILAS_POR_EXECUCAO, 11).",
    )
    p_gerar.add_argument(
        "--workflow", type=str, default="manual",
        help="Nome do workflow/origem desta execução, registado em PROJECT_STATE.md.",
    )

    subparsers.add_parser("status", help="Mostra o progresso actual da produção de apostilas.")
    subparsers.add_parser("validar-curriculo", help="Valida a integridade do mapa curricular oficial.")
    subparsers.add_parser("validar-ambiente", help="Valida as variáveis de ambiente obrigatórias.")

    return parser


def comando_validar_curriculo(settings: Settings) -> int:
    logger = get_logger("cli")
    try:
        curriculo = carregar_curriculo(settings.curriculum_file)
    except (FileNotFoundError, CurriculoInvalidoError) as exc:
        logger.error("Falha na validação do currículo: %s", exc)
        return 1
    logger.info(
        "Currículo válido: %d apostilas oficiais carregadas de %s.",
        len(curriculo), settings.curriculum_file,
    )
    return 0


def comando_validar_ambiente(settings: Settings) -> int:
    logger = get_logger("cli")
    try:
        settings.validate_required_for_generation()
    except EnvironmentError as exc:
        logger.error("Ambiente inválido: %s", exc)
        return 1
    logger.info("GEMINI_API_KEY configurada: %s", mask_secret(settings.gemini_api_key))
    logger.info("Modelo principal: %s | Modelo de reserva: %s", settings.gemini_model, settings.gemini_fallback_model)
    logger.info(
        "Limites configurados — RPM: %d | TPM: %d | RPD: %d",
        settings.gemini_rpm_limit, settings.gemini_tpm_limit, settings.gemini_rpd_limit,
    )
    logger.info("Ambiente validado com sucesso.")
    return 0


def comando_status(settings: Settings) -> int:
    logger = get_logger("cli")
    curriculo = carregar_curriculo(settings.curriculum_file)
    registro = RegistroDuplicidade(settings.registry_file)
    concluidos = registro.ids_concluidos()
    total = len(curriculo)
    proximo = curriculo.proximo_pendente(concluidos)

    logger.info("=== Estado da Produção de Apostilas EBE ===")
    logger.info("Total concluído: %d / %d (%.2f%%)", len(concluidos), total, (len(concluidos) / total) * 100)
    if proximo:
        logger.info("Próxima apostila pendente: %s — %s", proximo.codigo, proximo.titulo)
    else:
        logger.info("Currículo 100%% concluído. Nenhuma apostila pendente.")
    return 0


def comando_gerar_lote(settings: Settings, quantidade: int | None, workflow: str) -> int:
    logger = get_logger("cli")
    settings.validate_required_for_generation()
    settings.ensure_directories()

    quantidade_final = quantidade if quantidade is not None else settings.apostilas_por_execucao

    curriculo = carregar_curriculo(settings.curriculum_file)
    registro = RegistroDuplicidade(settings.registry_file)
    project_state_md = settings.data_dir.parent / "PROJECT_STATE.md"
    estado = GestorEstado(settings.state_file, project_state_md)
    estado.iniciar_execucao(workflow)

    rate_limiter = RateLimiter(
        rpm=settings.gemini_rpm_limit,
        tpm=settings.gemini_tpm_limit,
        rpd=settings.gemini_rpd_limit,
        estado_path=settings.data_dir / "rate_limit_state.json",
    )
    gemini_client = GeminiClient(settings, rate_limiter)
    docx_builder = ApostilaDocxBuilder(settings)

    fila = FilaProcessamentoApostilas(
        curriculo=curriculo,
        registro=registro,
        estado=estado,
        gemini_client=gemini_client,
        docx_builder=docx_builder,
    )

    logger.info(
        "Iniciando geração de lote: até %d apostilas pendentes (workflow=%s).",
        quantidade_final, workflow,
    )
    resultado = fila.processar_lote(quantidade_final)

    logger.info(
        "Lote concluído: %d sucesso(s), %d falha(s), interrompido_por_limite_diario=%s.",
        len(resultado.processadas_com_sucesso), len(resultado.falhadas),
        resultado.interrompido_por_limite_diario,
    )

    status_final = "concluido_com_erros" if resultado.falhadas else "concluido"
    if resultado.interrompido_por_limite_diario:
        status_final = "interrompido_limite_diario"
    estado.finalizar_execucao(status_final)

    # Código de saída 0 mesmo com falhas pontuais (registadas e retomáveis),
    # para que o workflow do GitHub Actions não marque a execução inteira
    # como falha quando o progresso real foi feito. Apenas erros de
    # ambiente/currículo (excepções não tratadas) resultam em saída != 0.
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _construir_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    configurar_logging(settings.logs_dir, nivel=logging.INFO)
    logger = get_logger("cli")

    try:
        if args.comando == "gerar-lote":
            return comando_gerar_lote(settings, args.quantidade, args.workflow)
        if args.comando == "status":
            return comando_status(settings)
        if args.comando == "validar-curriculo":
            return comando_validar_curriculo(settings)
        if args.comando == "validar-ambiente":
            return comando_validar_ambiente(settings)
    except Exception as exc:  # noqa: BLE001 — ponto de saída único da CLI
        logger.exception("Erro fatal na execução do comando '%s': %s", args.comando, exc)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
