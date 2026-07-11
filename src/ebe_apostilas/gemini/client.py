import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
import json

class GeracaoConteudoError(Exception):
    """Exceção personalizada para erros de geração de conteúdo."""
    pass

class GeminiClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
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
            raise GeracaoConteudoError(f"Erro Groq: {e}") from e

    # Compatibilidade com o resto do sistema
    def generate(self, prompt):
        return self.generate_content(prompt)