from typing import List


class TranscriptChunker:

    @staticmethod
    def chunk(transcript: list, chunk_size: int = 25) -> List[list]:
        return [
            transcript[i:i + chunk_size]
            for i in range(0, len(transcript), chunk_size)
        ]