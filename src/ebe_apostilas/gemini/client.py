import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

class GeracaoConteudoError(Exception):
    """Exceção personalizada para erros de geração de conteúdo."""
    pass

class GeminiClient:
    def __init__(self, settings=None, rate_limiter=None):
        # Aceita os parâmetros do código original (settings e rate_limiter)
        # mas usamos Groq
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

    # Compatibilidade total com o resto do sistema
    def generate(self, prompt):
        return self.generate_content(prompt)