import json


class JsonParser:

    @staticmethod
    def parse(text: str):

        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "")
            text = text.replace("```", "")

        return json.loads(text)