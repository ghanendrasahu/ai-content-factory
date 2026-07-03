import json

from app.ai.chunker import TranscriptChunker
from app.ai.llm import LLM
from app.ai.parser import JsonParser
from app.ai.prompts import CLIP_PROMPT


class ClipDetector:

    @staticmethod
    def detect(transcript: list):

        chunks = TranscriptChunker.chunk(transcript)

        clips = []

        for chunk in chunks:

            prompt = CLIP_PROMPT.format(
                transcript=json.dumps(chunk, indent=2)
            )

            for _ in range(3):

                try:

                    response = LLM.generate(prompt)

                    result = JsonParser.parse(response)

                    clips.extend(result)

                    break

                except Exception:
                    continue

        clips.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return clips[:5]