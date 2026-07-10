# CHANGELOG

Todas as alterações relevantes da plataforma `ebe_apostilas` são
documentadas neste ficheiro. Formato inspirado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.0.0] — 2026-07-10

### Adicionado

- Extracção integral e validada do mapa curricular oficial da EBE
  (`EBE_Mapa_Completo_Apostilas-2.pdf`) para `data/curriculo_apostilas.json`,
  com as **1.029 apostilas oficiais**, organizadas por Nível → Instituto →
  Escola → Curso → Módulo, sem lacunas nem duplicados.
- Núcleo (`ebe_apostilas.core`): configuração (`Settings`, validação de
  variáveis obrigatórias), modelos de dados tipados (Pydantic v2),
  carregamento/validação do currículo, logging estruturado com filtro
  automático de segredos, registo de controlo de duplicidade e gestor de
  checkpoint/estado com geração automática de `PROJECT_STATE.md`.
- Integração Gemini (`ebe_apostilas.gemini`): cliente de produção com
  retry e backoff exponencial (`tenacity`), controlo combinado de
  RPM/TPM/RPD com persistência do contador diário, fallback automático
  para modelo de reserva, sistema de prompts únicos por apostila (nunca
  reutilizando conteúdo entre apostilas) e fila de processamento
  sequencial com retomada automática.
- Geração de documentos (`ebe_apostilas.docx_gen`): biblioteca de estilos
  institucionais (paleta, tipografia Garamond, cabeçalho/rodapé com
  paginação automática), capa académica com quadro de identificação,
  marco filosófico, índice automático nativo do Word (campo `TOC`), e
  construtor completo da apostila (ficha técnica, apresentação,
  objectivos, versículo-chave, texto-base, desenvolvimento estruturado em
  quatro secções, quadro de destaque, aplicação prática, síntese,
  exercícios em três blocos, estudo bíblico complementar, resumo,
  glossário em tabela, bibliografia e anotações pessoais).
- CLI (`ebe_apostilas.cli`) com os comandos `gerar-lote`, `status`,
  `validar-curriculo` e `validar-ambiente`.
- Suíte de testes automatizados (`tests/`, `pytest`) cobrindo currículo,
  modelos, registo de duplicidade, rate limiter, prompts, cliente Gemini
  (mockado) e geração de documentos DOCX — 47 testes, sem dependência da
  API real.
- Workflows do GitHub Actions prontos em `workflows_ready/`:
  `producao-diaria-apostilas.yml` (geração diária de 11 apostilas, com
  commit automático dos resultados e retomada automática) e
  `ci-testes.yml` (validação contínua em Python 3.10/3.11/3.12).
- Scripts auxiliares (`scripts/setup_ambiente.sh`,
  `scripts/gerar_lote_local.sh`, `scripts/rodar_testes.sh`).
- Documentação: `README.md` (arquitectura e uso completo), `ROADMAP.md`
  (expansão futura) e este `CHANGELOG.md`.

### Segurança

- Nenhuma chave de API é armazenada no código-fonte; toda a configuração
  sensível é lida de variáveis de ambiente / GitHub Secrets, com validação
  explícita antes de qualquer execução real e filtro de segredos no
  logging.
