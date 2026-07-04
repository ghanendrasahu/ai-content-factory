import json
import re


class JsonParser:

    @staticmethod
    def parse(text: str):

        text = text.strip()

        # Remove markdown code fences
        text = text.replace("```json", "").replace("```", "").strip()

        # Extract the first JSON array if extra text is present
        match = re.search(r"\[.*\]", text, re.DOTALL)

        if match:
            text = match.group(0)

        return json.loads(text)