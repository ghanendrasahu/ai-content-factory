import json

from app.ai.llm import LLM
from app.ai.parser import JsonParser
from app.logger import logger

DEFAULT_CONTENT_PACK = {
    "title": "Generated Video",
    "description": "",
    "hashtags": [],
    "caption": "",
    "top_clips": [],
}


class ContentPackager:
    @staticmethod
    def generate(transcript: list, clips: list):
        prompt = f"""
You are a viral YouTube Shorts strategist.

Return ONLY valid JSON. No markdown. No explanation.

Schema:
{{
  "title": "",
  "description": "",
  "hashtags": ["#tag1", "#tag2"],
  "caption": "",
  "top_clips": [
    {{
      "title": "",
      "reason": ""
    }}
  ]
}}

Transcript:
{json.dumps(transcript)}

Clips:
{json.dumps(clips)}
"""

        for _ in range(2):
            try:
                response = LLM.generate(prompt)
                return ContentPackager._parse_response(response)
            except Exception as e:
                logger.warning("Content pack parse failed: %s", e)

        return DEFAULT_CONTENT_PACK.copy()

    @staticmethod
    def _parse_response(response: str):
        parsed = JsonParser.parse_object(response)
        if not isinstance(parsed, dict):
            raise ValueError("Content pack must be a JSON object")

        content_pack = DEFAULT_CONTENT_PACK.copy()
        content_pack.update(
            {
                "title": str(parsed.get("title") or content_pack["title"]),
                "description": str(parsed.get("description") or ""),
                "caption": str(parsed.get("caption") or ""),
            }
        )

        hashtags = parsed.get("hashtags")
        content_pack["hashtags"] = hashtags if isinstance(hashtags, list) else []

        top_clips = parsed.get("top_clips")
        content_pack["top_clips"] = top_clips if isinstance(top_clips, list) else []

        return content_pack
