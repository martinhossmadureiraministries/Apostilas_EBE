"""
Controlo de limites da API Gemini gratuita: RPM (pedidos por minuto), TPM
(tokens por minuto) e RPD (pedidos por dia).

O limitador é persistente entre execuções (ficheiro JSON), permitindo que o
contador de RPD sobreviva ao reinício do processo — essencial para
execuções agendadas em GitHub Actions, onde cada execução do workflow é um
processo novo mas partilha a mesma quota diária do projecto Gemini.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("ebe_apostilas.rate_limiter")


class LimiteDiarioExcedidoError(Exception):
    """Lançado quando o limite de pedidos por dia (RPD) foi atingido."""


@dataclass
class _JanelaDeslizante:
    """Janela deslizante genérica para contagem de eventos (pedidos ou
    tokens) num intervalo de tempo (por omissão, 60 segundos)."""

    intervalo_segundos: float
    eventos: deque = field(default_factory=deque)  # (timestamp, quantidade)

    def registar(self, quantidade: int = 1, agora: float | None = None) -> None:
        agora = agora if agora is not None else time.monotonic()
        self.eventos.append((agora, quantidade))
        self._purgar(agora)

    def _purgar(self, agora: float) -> None:
        limite = agora - self.intervalo_segundos
        while self.eventos and self.eventos[0][0] < limite:
            self.eventos.popleft()

    def total_atual(self, agora: float | None = None) -> int:
        agora = agora if agora is not None else time.monotonic()
        self._purgar(agora)
        return sum(q for _, q in self.eventos)

    def tempo_ate_liberar(self, quantidade_necessaria: int, limite: int, agora: float | None = None) -> float:
        """Tempo (segundos) a aguardar até que exista margem para mais
        ``quantidade_necessaria`` eventos sem ultrapassar ``limite``."""
        agora = agora if agora is not None else time.monotonic()
        self._purgar(agora)
        if self.total_atual(agora) + quantidade_necessaria <= limite:
            return 0.0
        if not self.eventos:
            return 0.0
        mais_antigo_ts, _ = self.eventos[0]
        espera = (mais_antigo_ts + self.intervalo_segundos) - agora
        return max(espera, 0.0)


class RateLimiter:
    """Controlador combinado de RPM, TPM e RPD para a API Gemini gratuita.

    Uso típico::

        limiter = RateLimiter(rpm=8, tpm=200_000, rpd=180,
                               estado_path=Path("data/rate_limit_state.json"))
        limiter.aguardar_e_reservar(tokens_estimados=3000)
        # ... chamar a API ...
    """

    def __init__(self, rpm: int, tpm: int, rpd: int, estado_path: Path):
        self._rpm_limite = rpm
        self._tpm_limite = tpm
        self._rpd_limite = rpd
        self._estado_path = estado_path
        self._lock = threading.Lock()

        self._janela_rpm = _JanelaDeslizante(intervalo_segundos=60.0)
        self._janela_tpm = _JanelaDeslizante(intervalo_segundos=60.0)

        self._rpd_data: str = ""
        self._rpd_contagem: int = 0
        self._carregar_estado_diario()

    # --- persistência do contador diário (RPD) ---
    def _data_hoje_pacific_like(self) -> str:
        # A quota diária da Gemini reinicia à meia-noite Pacific Time.
        # Para simplicidade e robustez em CI (sem tzdata garantida),
        # usamos UTC-8 como aproximação fixa e conservadora do Pacific
        # Standard Time, o que resulta numa margem de segurança adicional.
        from datetime import timedelta

        agora_utc = datetime.now(timezone.utc)
        aproximado_pacific = agora_utc - timedelta(hours=8)
        return aproximado_pacific.strftime("%Y-%m-%d")

    def _carregar_estado_diario(self) -> None:
        hoje = self._data_hoje_pacific_like()
        if self._estado_path.exists():
            try:
                bruto = json.loads(self._estado_path.read_text(encoding="utf-8"))
                if bruto.get("data") == hoje:
                    self._rpd_data = hoje
                    self._rpd_contagem = int(bruto.get("contagem", 0))
                    return
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        self._rpd_data = hoje
        self._rpd_contagem = 0
        self._persistir_estado_diario()

    def _persistir_estado_diario(self) -> None:
        self._estado_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._estado_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"data": self._rpd_data, "contagem": self._rpd_contagem}),
            encoding="utf-8",
        )
        tmp.replace(self._estado_path)

    def _revalidar_dia(self) -> None:
        hoje = self._data_hoje_pacific_like()
        if hoje != self._rpd_data:
            self._rpd_data = hoje
            self._rpd_contagem = 0
            self._persistir_estado_diario()

    def rpd_restante(self) -> int:
        with self._lock:
            self._revalidar_dia()
            return max(self._rpd_limite - self._rpd_contagem, 0)

    def aguardar_e_reservar(self, tokens_estimados: int) -> None:
        """Bloqueia (dormindo) o tempo necessário para respeitar RPM e TPM,
        e reserva uma unidade de RPD. Lança ``LimiteDiarioExcedidoError`` se
        o limite diário já tiver sido atingido."""
        with self._lock:
            self._revalidar_dia()
            if self._rpd_contagem >= self._rpd_limite:
                raise LimiteDiarioExcedidoError(
                    f"Limite diário de pedidos (RPD={self._rpd_limite}) atingido "
                    f"para esta execução. Retome amanhã ou na próxima execução "
                    f"agendada do workflow."
                )

            while True:
                agora = time.monotonic()
                espera_rpm = self._janela_rpm.tempo_ate_liberar(1, self._rpm_limite, agora)
                espera_tpm = self._janela_tpm.tempo_ate_liberar(
                    tokens_estimados, self._tpm_limite, agora
                )
                espera = max(espera_rpm, espera_tpm)
                if espera <= 0:
                    break
                logger.info(
                    "Rate limiting: aguardando %.1fs (RPM: %.1fs, TPM: %.1fs) "
                    "para respeitar os limites gratuitos da API Gemini.",
                    espera, espera_rpm, espera_tpm,
                )
                time.sleep(min(espera, 5.0))  # verifica periodicamente

            self._janela_rpm.registar(1)
            self._janela_tpm.registar(tokens_estimados)
            self._rpd_contagem += 1
            self._persistir_estado_diario()
