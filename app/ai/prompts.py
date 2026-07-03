CLIP_PROMPT = """
You are an expert YouTube Shorts editor.

Analyze the transcript.

Return ONLY valid JSON.

Find the 5 best clips.

Each clip must contain:

- title
- start
- end
- score (1-10)
- reason

Transcript:

{transcript}
"""