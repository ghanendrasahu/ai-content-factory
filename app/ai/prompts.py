CLIP_PROMPT = """
You are an expert YouTube Shorts editor.

Analyze ONLY the transcript below.

Find the BEST moments that would perform well as YouTube Shorts.

Score each clip based on:
- Hook (0-10)
- Information Value (0-10)
- Emotional Impact (0-10)
- Retention Potential (0-10)

Return ONLY valid JSON.

Example format:

[
  {{
    "title": "example",
    "start": 12.5,
    "end": 42.3,
    "score": 9.7,
    "reason": "why this clip works"
  }}
]

Transcript:

{transcript}
"""
