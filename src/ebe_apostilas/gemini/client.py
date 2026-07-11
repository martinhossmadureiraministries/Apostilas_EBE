import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

class GeracaoConteudoError(Exception):
    """Exceção personalizada para erros de geração de conteúdo."""
    pass

class GeminiClient:
    def __init__(self, settings=None, rate_limiter=None):
        self.settings = settings
        self.rate_limiter = rate_limiter

        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY ou GEMINI_API_KEY não está definida.")

        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
    def generate_content(self, prompt: str, **kwargs):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.7,
                max_tokens=8192,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            raise GeracaoConteudoError(f"Erro na geração com Groq: {str(e)}") from e

    # Método esperado pelo queue_manager
    def gerar_conteudo_apostila(self, item):
        """Método compatível com o sistema original."""
        titulo = getattr(item, 'titulo', str(item))
        prompt = f"""Gere uma apostila completa e original da Escola Bíblica Epignósis para o tema: {titulo}.

Siga rigorosamente o padrão institucional:
- Capa com identidade EBE
- Marco filosófico
- Ficha técnica
- Índice automático
- Desenvolvimento estruturado com quadros, tabelas e exercícios em 3 blocos (Compreensão, Reflexão, Ministério)
- Estudo bíblico complementar
- Glossário
- Bibliografia
- Anotações pessoais

Use português de Portugal/Angola (pt-PT), linguagem clara, teologicamente precisa e pastoral. Extensão: 15-20 páginas reais em .docx."""

        return self.generate_content(prompt)

    # Compatibilidade adicional
    def generate(self, prompt):
        return self.generate_content(prompt)