# EBE Apostilas — Plataforma Automática de Geração de Apostilas

Plataforma modular e totalmente automática para a geração das **1.029
apostilas** do mapa curricular oficial da **Escola Bíblica Epignósis
(EBE)**, utilizando exclusivamente a **API gratuita do Google Gemini**.

> Para a documentação dos materiais institucionais já produzidos
> (documentos oficiais, manuais, modelos, certificados, apostila-piloto),
> consulte [`LEIA-ME.md`](LEIA-ME.md).

---

## 1. Visão Geral

Cada apostila gerada:

- é **totalmente original** (nunca reutiliza texto entre apostilas);
- possui **15 a 20 páginas reais** em formato `.docx` editável;
- segue o **padrão editorial profissional** da EBE: capa institucional,
  marco filosófico, ficha técnica, índice automático, cabeçalho e rodapé
  com paginação, desenvolvimento estruturado, quadros de destaque,
  tabelas, exercícios em três blocos (compreensão, reflexão, ministério),
  estudo bíblico complementar, glossário, bibliografia e anotações
  pessoais;
- respeita **exactamente** o mapa curricular oficial (título, nível,
  instituto, escola, curso e módulo), sem jamais alterar ou reordenar o
  currículo.

A arquitetura é modular e está preparada para expandir-se, no futuro, a
outros tipos de materiais (e-books, manuais, avaliações, provas,
apresentações, planos de aula, guias de estudo e materiais
institucionais), reaproveitando a mesma infraestrutura de prompts, fila de
processamento, controlo de limites da API e geração de documentos.

## 2. Arquitectura

> **Nota sobre `assets/` e `_assets/`**: `assets/` é o directório de
> recursos oficial da nova plataforma (`ebe_apostilas.docx_gen`).
> `_assets/` é mantido apenas por **compatibilidade com os geradores
> institucionais legados** (`_estilos.py`, `apostila_piloto.py`,
> `doc1_missao_visao_valores.py` … `doc8_pre_requisitos.py`,
> `manual_aluno.py`, `manual_docente.py`, `modelo_*.py`), que já
> referenciam esse caminho. Ambos contêm exactamente os mesmos ficheiros
> de logotipo; não é uma duplicação acidental.

```
Apostilas_EBE/
├── data/
│   ├── curriculo_apostilas.json      # Mapa curricular oficial (1.029 apostilas) — fonte única de verdade
│   ├── registro_apostilas.json       # Controlo de duplicidade (ID, título, hash, versão, data, estado)
│   ├── estado_producao.json          # Checkpoint interno (retomada automática)
│   └── rate_limit_state.json         # Contador diário de pedidos (RPD) persistente
├── output/
│   └── apostilas/                    # Apostilas .docx geradas
├── logs/                             # Logs diários de execução
├── src/ebe_apostilas/
│   ├── core/                         # Configuração, modelos, currículo, logging, checkpoint, duplicidade
│   ├── gemini/                       # Cliente Gemini, prompts, rate limiter, fila de processamento
│   ├── docx_gen/                     # Estilos, capa, índice automático, construtor do documento final
│   └── cli/                          # Interface de linha de comando (ebe-apostilas)
├── tests/                            # Suíte de testes automatizados (pytest, com mocks da API Gemini)
├── scripts/                          # Scripts auxiliares (setup, geração local, testes)
├── workflows_ready/                  # Workflows do GitHub Actions prontos para uso (ver secção 5)
├── PROJECT_STATE.md                  # Estado da produção, actualizado automaticamente a cada execução
├── CHANGELOG.md
└── ROADMAP.md
```

### Princípios de design

- **SOLID / DRY / KISS**: cada módulo tem uma única responsabilidade
  (currículo, registo, estado, rate limiting, cliente Gemini, geração
  DOCX); nenhuma lógica é duplicada entre módulos.
- **Tipagem forte**: todos os modelos de dados usam Pydantic v2, com
  validação automática (ex.: código da apostila sempre coerente com o ID).
- **Falhas isoladas**: um erro numa apostila nunca interrompe o lote —
  fica registado, e a apostila é retomada automaticamente na próxima
  execução.
- **Nenhum segredo no código**: a chave da API é lida exclusivamente de
  variáveis de ambiente / GitHub Secrets.

## 3. Instalação e uso local

```bash
# 1. Configurar o ambiente
./scripts/setup_ambiente.sh --dev

# 2. Configurar a chave da API Gemini (gratuita)
cp .env.example .env
# edite .env e preencha GEMINI_API_KEY (obtida em https://aistudio.google.com/apikey)

# 3. Validar o ambiente e o currículo
source .venv/bin/activate
ebe-apostilas validar-curriculo
ebe-apostilas validar-ambiente

# 4. Ver o progresso actual
ebe-apostilas status

# 5. Gerar o próximo lote de apostilas pendentes (padrão: 11)
./scripts/gerar_lote_local.sh
# ou, para uma quantidade específica:
./scripts/gerar_lote_local.sh 3
```

## 4. Comandos da CLI

| Comando | Descrição |
|---|---|
| `ebe-apostilas validar-curriculo` | Valida a integridade das 1.029 apostilas oficiais (sem lacunas nem duplicados). |
| `ebe-apostilas validar-ambiente` | Valida `GEMINI_API_KEY` e mostra a configuração de modelos/limites. |
| `ebe-apostilas status` | Mostra o progresso actual (concluídas / total, próxima apostila). |
| `ebe-apostilas gerar-lote [--quantidade N] [--workflow NOME]` | Gera até N apostilas pendentes, em ordem curricular, com retomada automática. |

## 5. GitHub Actions

Os workflows prontos encontram-se em `workflows_ready/`. **Para
activá-los**, copie-os (sem qualquer modificação) para
`.github/workflows/`, mantendo exactamente os mesmos nomes de ficheiro:

```bash
mkdir -p .github/workflows
cp workflows_ready/producao-diaria-apostilas.yml .github/workflows/
cp workflows_ready/ci-testes.yml .github/workflows/
git add .github/workflows/
git commit -m "ci: activar workflows de produção diária e testes"
git push
```

> Nota: nesta sessão de trabalho automatizada, a conta do agente não possui
> permissão `workflows` do GitHub para escrever directamente em
> `.github/workflows/`. Por isso, os workflows foram entregues prontos em
> `workflows_ready/`, com os nomes finais exactos, para serem movidos
> manualmente por um mantenedor com permissão adequada — depois de
> movidos, funcionam sem qualquer alteração.

### `producao-diaria-apostilas.yml`

- Executa **diariamente às 03:00 UTC** (também disponível via
  `workflow_dispatch` para execução manual).
- Gera **exactamente 11 apostilas por execução** (configurável via
  variável de repositório `APOSTILAS_POR_EXECUCAO` ou input manual).
- Valida o ambiente antes de gerar; nunca falha "vermelho" por causa de
  apostilas individuais com erro (ficam registadas e são retomadas
  automaticamente).
- Faz commit e push automático de `data/`, `output/`, `logs/` e
  `PROJECT_STATE.md` de volta ao repositório.
- Publica os logs da execução como artefacto.

### `ci-testes.yml`

- Executa a suíte de testes automatizados em cada `push`/`pull_request`,
  em Python 3.10, 3.11 e 3.12.
- Valida a integridade do currículo oficial.
- Verifica qualidade de código (`ruff`) e tipagem estática (`mypy`).

### GitHub Secrets necessários

| Nome | Obrigatório | Descrição |
|---|---|---|
| `GEMINI_API_KEY` | **Sim** | Chave gratuita da API Google Gemini (https://aistudio.google.com/apikey). |

### GitHub Variables (opcionais, com valores padrão seguros)

| Nome | Padrão | Descrição |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Modelo principal. |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.0-flash` | Modelo de reserva. |
| `GEMINI_RPM_LIMIT` | `8` | Pedidos por minuto (margem de segurança). |
| `GEMINI_TPM_LIMIT` | `200000` | Tokens de entrada por minuto. |
| `GEMINI_RPD_LIMIT` | `180` | Pedidos por dia reservados a esta execução. |
| `APOSTILAS_POR_EXECUCAO` | `11` | Apostilas geradas por execução diária. |

## 6. Controlo de limites da API gratuita

O módulo `ebe_apostilas.gemini.rate_limiter` implementa:

- **RPM** (pedidos por minuto) e **TPM** (tokens por minuto) via janelas
  deslizantes em memória;
- **RPD** (pedidos por dia) persistido em `data/rate_limit_state.json`,
  sobrevivendo a reinícios do processo (essencial em GitHub Actions, onde
  cada execução é um processo novo);
- **retry com backoff exponencial** (via `tenacity`) para erros `429` e
  `5xx`, com número máximo de tentativas configurável;
- **fallback automático** para um segundo modelo Gemini quando o modelo
  principal falha persistentemente ou o conteúdo gerado é insuficiente;
- interrupção **limpa e correcta** do lote quando o limite diário é
  atingido, sem perda de progresso — a próxima execução retoma
  automaticamente do ponto exacto onde parou.

## 7. Controlo de duplicidade

`data/registro_apostilas.json` regista, para cada apostila processada:
ID, título, hash SHA-256 do conteúdo gerado, versão, data de conclusão e
estado (`concluida` / `erro`). Antes de processar qualquer apostila, o
sistema consulta este registo e **nunca reprocessa uma apostila já
concluída**.

## 8. Checkpoint e retomada automática

`data/estado_producao.json` e `PROJECT_STATE.md` (na raiz do repositório)
são actualizados a cada execução com: última apostila concluída, próxima
apostila, progresso percentual, data, versão da plataforma, estado e
erros da execução. Qualquer execução — manual ou agendada — retoma
automaticamente a partir da apostila pendente mais antiga, sem exigir
qualquer intervenção manual.

## 9. Testes

```bash
./scripts/rodar_testes.sh
```

A suíte cobre: integridade do currículo oficial, modelos de dados,
registo de duplicidade, rate limiter, prompts, cliente Gemini (com mocks
— nunca chama a API real) e geração de documentos DOCX (validação
estrutural do ficheiro OOXML gerado).

## 10. Segurança

- A chave da API **nunca** é escrita no código-fonte, nem registada em
  logs (filtro automático de segredos no `logging_config`).
- Variáveis obrigatórias são validadas explicitamente antes de qualquer
  chamada real à API (`ebe-apostilas validar-ambiente`).
- Em produção, a chave só deve existir como **GitHub Secret**.

## 11. Expansão futura

A arquitetura modular (prompts + fila + rate limiter + gerador DOCX)
está pronta para suportar, com a criação de novos módulos de prompt e
templates de documento (sem alterar o núcleo): livros, e-books, manuais,
avaliações, provas, apresentações, planos de aula, guias de estudo e
outros materiais institucionais. Ver [`ROADMAP.md`](ROADMAP.md).
