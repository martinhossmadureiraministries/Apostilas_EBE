"""
Sistema de prompts para a geração de apostilas via Gemini.

Cada apostila recebe um prompt único, construído dinamicamente a partir dos
metadados curriculares (nível, instituto, escola, curso, módulo e título),
garantindo originalidade total do conteúdo — nunca reaproveitando texto
entre apostilas nem se limitando a substituir apenas o título.
"""
from __future__ import annotations

from ebe_apostilas.core.models import ItemCurricular

IDENTIDADE_INSTITUCIONAL = """\
Escola Bíblica Epignósis (EBE) — ἐπίγνωσις.
Lema: "Conhecer a Deus. Viver a Palavra. Manifestar o Reino."
Marco filosófico: "Acreditamos que o verdadeiro conhecimento de Deus \
transforma a mente pela verdade das Escrituras, o coração pela acção do \
Espírito Santo e a vida pelo compromisso de viver e anunciar o Evangelho \
de Jesus Cristo."
Língua: português europeu/Angola (pt-PT). Versão bíblica de referência: \
Almeida Revista e Corrigida (ARC). Estilo: académico formal, pastoral e \
didáctico, nunca superficial.
Eixos pedagógicos institucionais: CONHECER (compreensão doutrinária e \
bíblica), CRER (convicção espiritual), VIVER (aplicação pessoal), \
SERVIR (aplicação ministerial e comunitária).
"""

INSTRUCOES_ORIGINALIDADE = """\
REGRAS DE ORIGINALIDADE (obrigatórias e não negociáveis):
1. O conteúdo desta apostila deve ser 100% original e escrito especificamente \
para este título e este contexto curricular — nunca reutilize frases, \
estruturas de parágrafo ou exemplos de outras apostilas.
2. Não é permitido gerar um texto genérico que apenas troque o título: o \
desenvolvimento deve tratar exclusivamente do tema exacto indicado, com \
profundidade teológica, exegese bíblica concreta (referências reais e \
verificáveis, com livro, capítulo e versículo), e aplicação prática real.
3. Utilize sempre citações bíblicas fiéis à versão Almeida Revista e \
Corrigida (ARC), com referência completa (Livro Capítulo:Versículo).
4. Toda a bibliografia recomendada deve conter apenas obras e autores \
reais e reconhecidos na literatura teológica evangélica (ex.: Gordon Fee, \
Douglas Stuart, Henry Virkler, Louis Berkhof, Wayne Grudem, Millard \
Erickson, Augustus Nicodemus Lopes, John Stott, R.C. Sproul, entre outros \
autores genuínos e adequados ao tema), nunca invente títulos ou autores \
fictícios.
5. O texto deve ser extenso e substancial o suficiente para preencher \
entre 15 e 20 páginas reais de um documento A4 profissional (aproximadamente \
5.000 a 7.000 palavras no total, distribuídas entre todas as secções).
6. Nunca inclua marcações de markdown (##, **, etc.), símbolos de \
formatação, comentários sobre a própria tarefa, ou textos de preenchimento \
como "[inserir aqui]" — entregue apenas o conteúdo final, pronto para \
publicação.
"""

ESTRUTURA_JSON_INSTRUCOES = """\
Devolva EXCLUSIVAMENTE um objecto JSON válido, sem nenhum texto antes ou \
depois, respeitando rigorosamente o esquema fornecido. Todos os campos de \
texto devem estar em português europeu/Angola, num registo académico, \
pastoral e claro. Nenhum campo pode ficar vazio, genérico ou com \
reticências de preenchimento.

Directrizes de conteúdo por campo:
- "apresentacao": 2 a 3 parágrafos completos apresentando o tema aos alunos.
- "objectivos": 4 objectivos de aprendizagem, um para cada eixo CONHECER, \
CRER, VIVER, SERVIR, cada um começando pela palavra em maiúsculas (ex.: \
"CONHECER — ...").
- "introducao": 3 a 4 parágrafos substanciais introduzindo o tema com \
fundamentação bíblica inicial.
- "desenvolvimento": lista de exactamente 4 secções (numeradas \
implicitamente pela ordem), cada uma com "titulo" e "conteudo" com pelo \
menos 4 parágrafos densos, incluindo pelo menos uma citação bíblica com \
referência em cada secção, exegese, contexto histórico/cultural quando \
pertinente, e ligação com a vida cristã prática.
- "quadro_destaque_texto": uma frase-síntese memorável e profunda sobre o \
tema, adequada para um quadro de destaque.
- "aplicacao_pratica": 5 itens de aplicação prática concreta, cobrindo \
vida pessoal, família, igreja local, trabalho/sociedade e ministério.
- "sintese": 2 a 3 parágrafos de conclusão e síntese teológica do tema.
- "exercicios_compreensao": 5 perguntas objectivas sobre o conteúdo.
- "exercicios_reflexao": 3 perguntas de reflexão pessoal.
- "exercicios_ministerio": 2 perguntas de aplicação ministerial/serviço.
- "estudo_biblico_titulo": título de um estudo bíblico complementar \
directamente ligado ao tema, com uma passagem bíblica real e específica.
- "estudo_biblico_texto": 1 a 2 parágrafos introduzindo essa passagem.
- "estudo_biblico_perguntas": 5 perguntas de estudo indutivo sobre essa \
passagem.
- "resumo_final": 1 parágrafo de encerramento espiritual e motivacional.
- "glossario": 6 termos técnicos ou teológicos relevantes ao tema, cada um \
com definição precisa de 1 a 2 frases.
- "bibliografia": 5 referências bibliográficas reais, no formato \
AUTOR. Título da obra. Cidade: Editora.
"""


def construir_prompt_apostila(item: ItemCurricular) -> str:
    """Constrói o prompt completo e único para a geração do conteúdo de
    uma apostila específica, a partir dos seus metadados curriculares."""
    return f"""\
Você é o corpo docente da Escola Bíblica Epignósis (EBE), responsável por \
redigir apostilas didácticas oficiais, teologicamente sólidas, bíblicas e \
pastoralmente maduras.

{IDENTIDADE_INSTITUCIONAL}

CONTEXTO CURRICULAR DESTA APOSTILA (não alterar nem reinterpretar):
- Nível formativo: {item.nivel_nome}
- Instituto: {item.instituto_nome}
- Escola: {item.escola_nome}
- Curso: {item.curso_nome} (carga horária do curso: {item.carga_horaria_curso})
- Módulo {item.modulo_numero}: {item.modulo_nome}
- Apostila n.º {item.id} (código {item.codigo}) — TÍTULO EXACTO A DESENVOLVER: \
"{item.titulo}"

A sua tarefa é escrever o conteúdo completo e original desta apostila, \
tratando especificamente do tema "{item.titulo}" dentro do contexto do \
módulo "{item.modulo_nome}" e do curso "{item.curso_nome}". Não escreva \
sobre outro tema, não generalize, e não produza um texto que serviria \
igualmente para qualquer outra apostila do currículo.

{INSTRUCOES_ORIGINALIDADE}

{ESTRUTURA_JSON_INSTRUCOES}

Campos adicionais obrigatórios no JSON:
- "titulo": exactamente "{item.titulo}".
- "subtitulo": um subtítulo curto e evocativo, criado especificamente para \
este tema (nunca genérico).
- "versiculo_chave_texto" e "versiculo_chave_referencia": um versículo \
bíblico real, central ao tema, em texto ARC e referência completa.
- "texto_base_referencia": uma passagem bíblica real (referência de \
intervalo, ex.: "Romanos 8.1-17") indicada como leitura prévia, coerente \
com o tema.

Produza agora o JSON completo desta apostila.
"""
