"""
ebe_apostilas
=============

Plataforma modular e automática para a geração das apostilas curriculares da
Escola Bíblica Epignósis (EBE), utilizando exclusivamente a API gratuita do
Google Gemini.

A arquitetura é organizada em subpacotes independentes e reutilizáveis:

- ``ebe_apostilas.core``      — configuração, modelos de dados, currículo,
  logging, checkpoint/estado e controlo de duplicidade.
- ``ebe_apostilas.gemini``    — cliente Gemini com retry, backoff exponencial
  e controlo de limites (RPM/TPM/RPD), fila de processamento e prompts.
- ``ebe_apostilas.docx_gen``  — geração de documentos DOCX profissionais
  (capa, sumário, cabeçalho/rodapé, estilos, exercícios, glossário etc.).
- ``ebe_apostilas.cli``       — interface de linha de comando para execução
  local e em GitHub Actions.

O pacote foi desenhado para ser extensível a outros tipos de materiais
(e-books, manuais, avaliações, provas, apresentações, planos de aula, guias
de estudo e materiais institucionais) através da mesma infraestrutura de
geração, fila e controlo de limites.
"""

__version__ = "1.0.0"
