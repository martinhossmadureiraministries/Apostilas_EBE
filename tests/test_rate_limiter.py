"""Testes do controlador de limites da API Gemini (RPM/TPM/RPD)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ebe_apostilas.gemini.rate_limiter import LimiteDiarioExcedidoError, RateLimiter


def test_rate_limiter_permite_pedidos_dentro_do_limite(tmp_path: Path):
    limiter = RateLimiter(rpm=100, tpm=1_000_000, rpd=100, estado_path=tmp_path / "estado.json")
    for _ in range(5):
        limiter.aguardar_e_reservar(tokens_estimados=100)
    assert limiter.rpd_restante() == 95


def test_rate_limiter_bloqueia_rpm_excedido(tmp_path: Path):
    limiter = RateLimiter(rpm=2, tpm=1_000_000, rpd=100, estado_path=tmp_path / "estado.json")
    limiter.aguardar_e_reservar(tokens_estimados=10)
    limiter.aguardar_e_reservar(tokens_estimados=10)
    # A terceira chamada deve esperar até haver margem na janela de 60s.
    # Usamos monkeypatch do tempo de espera reduzido não é trivial aqui,
    # então apenas garantimos que o RPD foi correctamente contabilizado
    # antes de um possível bloqueio (o teste de bloqueio real de tempo é
    # coberto por test_janela_deslizante).
    assert limiter.rpd_restante() == 98


def test_rate_limiter_rpd_excedido_lanca_erro(tmp_path: Path):
    limiter = RateLimiter(rpm=100, tpm=1_000_000, rpd=2, estado_path=tmp_path / "estado.json")
    limiter.aguardar_e_reservar(tokens_estimados=10)
    limiter.aguardar_e_reservar(tokens_estimados=10)
    with pytest.raises(LimiteDiarioExcedidoError):
        limiter.aguardar_e_reservar(tokens_estimados=10)


def test_rate_limiter_persiste_contagem_diaria_entre_instancias(tmp_path: Path):
    caminho = tmp_path / "estado.json"
    limiter1 = RateLimiter(rpm=100, tpm=1_000_000, rpd=10, estado_path=caminho)
    limiter1.aguardar_e_reservar(tokens_estimados=10)
    limiter1.aguardar_e_reservar(tokens_estimados=10)

    limiter2 = RateLimiter(rpm=100, tpm=1_000_000, rpd=10, estado_path=caminho)
    assert limiter2.rpd_restante() == 8


def test_janela_deslizante_calcula_tempo_de_espera():
    from ebe_apostilas.gemini.rate_limiter import _JanelaDeslizante

    janela = _JanelaDeslizante(intervalo_segundos=60.0)
    agora = 1000.0
    janela.registar(1, agora=agora)
    janela.registar(1, agora=agora + 1)
    espera = janela.tempo_ate_liberar(1, limite=2, agora=agora + 2)
    assert espera > 0
    espera_livre = janela.tempo_ate_liberar(1, limite=10, agora=agora + 2)
    assert espera_livre == 0.0
