import json
import re


class JsonParser:

    @staticmethod
    def parse(text: str):
        if not text or not text.strip():
            raise ValueError("JSON response is empty")

        text = text.strip()

        # Remove markdown code fences
        text = text.replace("```json", "").replace("```", "").strip()

        # Extract the first JSON array if extra text is present
        match = re.search(r"\[.*\]", text, re.DOTALL)

        if match:
            text = match.group(0)

        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("Expected JSON array")

        return parsed

    @staticmethod
    def parse_object(text: str):
        if not text or not text.strip():
            raise ValueError("JSON response is empty")

        text = text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        if text.startswith("["):
            raise ValueError("Expected JSON object")

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            text = match.group(0)

        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")

        return parsed
