# ROADMAP — Plataforma EBE Apostilas

Este roteiro descreve a evolução planeada da plataforma, a partir da base
modular já implementada (currículo, geração via Gemini, geração DOCX,
fila, controlo de limites, checkpoint e duplicidade).

## Fase 1 — Produção das 1.029 Apostilas (em curso)

- [x] Extracção e validação do mapa curricular oficial (1.029 apostilas).
- [x] Motor de geração de conteúdo via API gratuita do Google Gemini.
- [x] Gerador de documentos DOCX com padrão editorial profissional.
- [x] Controlo de limites (RPM/TPM/RPD), retry e backoff exponencial.
- [x] Controlo de duplicidade e checkpoint com retomada automática.
- [x] Workflow diário de produção (11 apostilas/dia) pronto em
      `workflows_ready/`.
- [ ] Produção completa das 1.029 apostilas (≈ 94 dias de execução diária
      a 11 apostilas/dia, respeitando os limites gratuitos da API).
- [ ] Revisão pedagógica e doutrinária amostral do lote gerado, por
      Coordenação Acadêmica e Conselho Doutrinário da EBE.

## Fase 2 — Ampliação de Formatos de Material

A arquitectura modular (currículo → prompt → Gemini → geração de
documento) permite adicionar novos tipos de material reaproveitando o
mesmo núcleo (`core`), a mesma integração Gemini (`gemini`) e a mesma
biblioteca de estilos institucionais (`docx_gen.styles`):

- [ ] **E-books**: agregação de apostilas de um mesmo curso num volume
      único, com sumário consolidado (reaproveitando `compendio_merge.py`
      como referência de fusão de documentos).
- [ ] **Manuais**: extensão do gerador para estruturas de capítulos mais
      longas (seguindo o padrão já usado em `EBE-MAN-ALU` / `EBE-MAN-DOC`).
- [ ] **Avaliações e provas**: novo módulo de prompt orientado a geração
      de questões (múltipla escolha, dissertativas, práticas), com banco
      de questões versionado e controlo de duplicidade próprio.
- [ ] **Apresentações**: gerador `.pptx` (novo submódulo
      `ebe_apostilas.pptx_gen`), reaproveitando a paleta institucional.
- [ ] **Planos de aula**: geração automática a partir do conteúdo já
      produzido de cada apostila (cronograma das 5 fases da aula
      Epignósis).
- [ ] **Guias de estudo**: versões resumidas das apostilas, focadas em
      auto-estudo e grupos pequenos.
- [ ] **Materiais institucionais adicionais**: extensão dos geradores já
      existentes (`doc1_missao_visao_valores.py` … `doc8_pre_requisitos.py`)
      para o novo pacote `ebe_apostilas`, quando novos documentos
      institucionais forem requeridos.

## Fase 3 — Qualidade e Operação Contínua

- [ ] Painel de acompanhamento (dashboard estático gerado a partir de
      `PROJECT_STATE.md` e `data/registro_apostilas.json`), publicado via
      GitHub Pages.
- [ ] Verificação automática de qualidade textual (extensão mínima,
      presença de citações bíblicas válidas, ausência de marcações
      indevidas) como etapa adicional de validação antes da gravação do
      DOCX.
- [ ] Processo de revisão humana assistida: marcação de apostilas para
      revisão pedagógica/doutrinária prioritária, com estado adicional no
      registo de duplicidade (`em_revisao`).
- [ ] Suporte a múltiplas chaves Gemini rotativas (quando disponíveis),
      mantendo a mesma arquitectura de rate limiting por chave.
- [ ] Internacionalização opcional dos prompts (outras variantes do
      português ou outros idiomas), preservando o currículo oficial em
      português europeu/Angola como fonte única de verdade.

## Princípios que orientam toda a expansão

1. O **mapa curricular nunca é gerado ou alterado automaticamente** —
   qualquer novo curso/módulo/apostila deve ser adicionado por decisão
   institucional explícita, revisado e versionado em
   `data/curriculo_apostilas.json` (ou ficheiro equivalente para o novo
   tipo de material).
2. Toda nova capacidade de geração deve **reutilizar** o núcleo existente
   (`core`, `gemini`, `docx_gen.styles`) em vez de duplicar lógica.
3. Nenhuma capacidade nova deve introduzir segredos no código-fonte —
   toda credencial permanece exclusivamente em GitHub Secrets.
4. Toda nova fila de geração deve implementar checkpoint e controlo de
   duplicidade próprios, seguindo o padrão de
   `RegistroDuplicidade` / `GestorEstado`.
