"""
Modelos de dados (Pydantic) usados em toda a plataforma.

Estes modelos garantem tipagem forte, validação automática e serialização
consistente entre o mapa curricular, o motor de geração Gemini, o gerador
DOCX e o sistema de controlo de execução/duplicidade.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StatusApostila(str, Enum):
    """Ciclo de vida de uma apostila no pipeline de produção."""

    PENDENTE = "pendente"
    EM_PROCESSAMENTO = "em_processamento"
    CONCLUIDA = "concluida"
    ERRO = "erro"


class ItemCurricular(BaseModel):
    """Uma entrada do mapa curricular oficial (uma apostila a produzir).

    Este modelo espelha exactamente a estrutura extraída do documento
    institucional ``EBE_Mapa_Completo_Apostilas-2.pdf`` (EBE-PLAN-APO):
    Nível → Instituto → Escola → Curso → Módulo → Apostila. Nenhum campo
    aqui pode ser alterado por geração automática — o currículo é fixo e
    somente lido.
    """

    id: int = Field(..., ge=1, le=1029, description="Número sequencial oficial da apostila (1 a 1029).")
    codigo: str = Field(..., description="Código institucional, ex.: EBE-APO-0001.")
    titulo: str
    nivel_numero: int
    nivel_nome: str
    instituto_numero: int
    instituto_nome: str
    escola_id: int
    escola_nome: str
    curso_id: int
    curso_nome: str
    carga_horaria_curso: str
    modulo_numero: int
    modulo_nome: str

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str, info) -> str:
        esperado = f"EBE-APO-{info.data.get('id', 0):04d}"
        if v != esperado:
            raise ValueError(f"Código inconsistente: esperado {esperado}, recebido {v}")
        return v


class SecaoGerada(BaseModel):
    """Uma secção de conteúdo textual gerado pelo Gemini para a apostila."""

    titulo: str
    conteudo: str


class ExercicioBloco(BaseModel):
    """Um bloco de exercícios (compreensão, reflexão ou ministério)."""

    titulo: str
    perguntas: list[str] = Field(default_factory=list)


class TermoGlossario(BaseModel):
    termo: str
    definicao: str


class ConteudoApostilaGerado(BaseModel):
    """Estrutura completa do conteúdo textual de uma apostila, tal como
    devolvido (e validado) pela API Gemini, pronta para ser convertida em
    DOCX pelo módulo ``docx_gen``.
    """

    titulo: str
    subtitulo: str = ""
    versiculo_chave_texto: str
    versiculo_chave_referencia: str
    texto_base_referencia: str
    apresentacao: str
    objectivos: list[str] = Field(default_factory=list)
    introducao: str
    desenvolvimento: list[SecaoGerada] = Field(default_factory=list)
    quadro_destaque_titulo: str = "Para reter"
    quadro_destaque_texto: str
    aplicacao_pratica: list[str] = Field(default_factory=list)
    sintese: str
    exercicios_compreensao: list[str] = Field(default_factory=list)
    exercicios_reflexao: list[str] = Field(default_factory=list)
    exercicios_ministerio: list[str] = Field(default_factory=list)
    estudo_biblico_titulo: str
    estudo_biblico_texto: str
    estudo_biblico_perguntas: list[str] = Field(default_factory=list)
    resumo_final: str
    glossario: list[TermoGlossario] = Field(default_factory=list)
    bibliografia: list[str] = Field(default_factory=list)

    def contagem_palavras(self) -> int:
        """Estima o número total de palavras do conteúdo textual gerado,
        usado para verificar se a apostila atinge o volume mínimo exigido
        (15 a 20 páginas reais)."""
        partes: list[str] = [
            self.apresentacao,
            self.introducao,
            self.quadro_destaque_texto,
            self.sintese,
            self.estudo_biblico_texto,
            self.resumo_final,
        ]
        partes.extend(self.objectivos)
        partes.extend(self.aplicacao_pratica)
        partes.extend(self.exercicios_compreensao)
        partes.extend(self.exercicios_reflexao)
        partes.extend(self.exercicios_ministerio)
        partes.extend(self.estudo_biblico_perguntas)
        partes.extend(self.bibliografia)
        for sec in self.desenvolvimento:
            partes.append(sec.titulo)
            partes.append(sec.conteudo)
        for termo in self.glossario:
            partes.append(termo.termo)
            partes.append(termo.definicao)
        return sum(len(p.split()) for p in partes if p)


class RegistroApostila(BaseModel):
    """Entrada do registo de controlo de duplicidade
    (``data/registro_apostilas.json``).

    Garante que nenhuma apostila já concluída seja gerada novamente,
    registando ID, título, hash de conteúdo, versão, data e estado.
    """

    id: int
    codigo: str
    titulo: str
    hash_conteudo: str
    versao: int = 1
    data_conclusao: str
    status: StatusApostila
    caminho_docx: Optional[str] = None
    tentativas: int = 0
    ultimo_erro: Optional[str] = None
    palavras: int = 0
    modelo_usado: Optional[str] = None

    @staticmethod
    def calcular_hash(texto: str) -> str:
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    @staticmethod
    def agora_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
