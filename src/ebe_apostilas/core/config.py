"""
Configuração central da plataforma.

Todas as opções sensíveis (como a chave da API Gemini) são lidas
exclusivamente de variáveis de ambiente / GitHub Secrets — nunca do código
fonte. A chave nunca é registada em logs nem persistida em disco.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório (dois níveis acima de src/ebe_apostilas/core/config.py)
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configurações de execução da plataforma EBE Apostilas.

    Os valores podem ser fornecidos via variáveis de ambiente ou ficheiro
    ``.env`` (apenas em ambiente local — nunca em produção/CI). Em GitHub
    Actions, todos os segredos devem vir de ``secrets.*`` injectados como
    variáveis de ambiente do job.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Credenciais (OBRIGATÓRIO via GitHub Secrets) ===
    gemini_api_key: str = Field(
        default="",
        description="Chave da API gratuita do Google Gemini (GEMINI_API_KEY). "
        "Nunca deve ser escrita no código-fonte.",
    )

    # === Modelo Gemini ===
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Modelo Gemini usado para geração de conteúdo textual.",
    )
    gemini_fallback_model: str = Field(
        default="gemini-2.0-flash",
        description="Modelo de reserva, usado quando o modelo principal "
        "esgota a quota do dia (RPD) ou falha persistentemente.",
    )

    # === Controlo de limites da API gratuita (RPM / TPM / RPD) ===
    gemini_rpm_limit: int = Field(default=8, description="Pedidos por minuto (margem de segurança sobre o limite gratuito de 10-15).")
    gemini_tpm_limit: int = Field(default=200_000, description="Tokens de entrada por minuto (margem de segurança).")
    gemini_rpd_limit: int = Field(default=180, description="Pedidos por dia reservados para esta execução (margem de segurança sobre o limite gratuito de 250-1500).")
    gemini_max_output_tokens: int = Field(default=8192, description="Máximo de tokens de saída por apostila/secção.")
    gemini_temperature: float = Field(default=0.85, description="Temperatura de geração — favorece originalidade sem perder coerência.")

    # === Retry / backoff exponencial ===
    retry_max_attempts: int = Field(default=6, description="Número máximo de tentativas por chamada à API.")
    retry_initial_backoff_seconds: float = Field(default=4.0, description="Atraso inicial do backoff exponencial.")
    retry_max_backoff_seconds: float = Field(default=120.0, description="Atraso máximo do backoff exponencial.")
    retry_backoff_multiplier: float = Field(default=2.0, description="Multiplicador do backoff exponencial.")

    # === Produção diária (workflow GitHub Actions) ===
    apostilas_por_execucao: int = Field(default=11, description="Número de apostilas geradas por execução diária do workflow.")

    # === Caminhos ===
    data_dir: Path = Field(default=REPO_ROOT / "data")
    output_dir: Path = Field(default=REPO_ROOT / "output" / "apostilas")
    logs_dir: Path = Field(default=REPO_ROOT / "logs")
    assets_dir: Path = Field(default=REPO_ROOT / "assets")
    state_file: Path = Field(default=REPO_ROOT / "data" / "estado_producao.json")
    registry_file: Path = Field(default=REPO_ROOT / "data" / "registro_apostilas.json")
    curriculum_file: Path = Field(default=REPO_ROOT / "data" / "curriculo_apostilas.json")

    @field_validator("gemini_api_key")
    @classmethod
    def _strip_key(cls, v: str) -> str:
        return v.strip() if v else v

    def validate_required_for_generation(self) -> None:
        """Valida variáveis obrigatórias antes de qualquer execução real
        contra a API Gemini. Lança ``EnvironmentError`` com mensagem clara
        se a chave não estiver configurada.
        """
        if not self.gemini_api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY não está definida. Configure-a como "
                "GitHub Secret (Settings → Secrets and variables → Actions) "
                "e injecte-a como variável de ambiente no workflow, ou "
                "defina-a localmente em um ficheiro .env (nunca em código)."
            )

    def ensure_directories(self) -> None:
        """Garante que todos os directórios de trabalho existem."""
        for d in (self.data_dir, self.output_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Fábrica de configurações. Lê variáveis de ambiente a cada chamada,
    permitindo reconfiguração dinâmica em testes."""
    return Settings()


def mask_secret(value: Optional[str]) -> str:
    """Mascara um segredo para exibição segura em logs/mensagens."""
    if not value:
        return "<não definido>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
