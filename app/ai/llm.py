from groq import Groq

from app.config import settings

client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None


class LLM:

    @staticmethod
    def generate(prompt: str):
        if client is None:
            raise RuntimeError("GROQ_API_KEY is not configured")

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content
