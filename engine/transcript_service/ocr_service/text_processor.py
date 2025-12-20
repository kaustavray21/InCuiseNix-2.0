import re
from difflib import SequenceMatcher
from typing import List, Optional

class TextProcessor:
    def __init__(self, min_similarity: float = 0.85):
        self.min_similarity = min_similarity

    def clean_text(self, text: str) -> str:
        """
        Basic cleaning: removes excessive whitespace, non-printable characters,
        and fixes common OCR artifacts.
        """
        if not text:
            return ""

        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove non-printable characters (keeping basic punctuation)
        text = "".join(char for char in text if char.isprintable())
        
        return text

    def remove_duplicates(self, segments: List[str]) -> List[str]:
        """
        Deduplicates a list of text segments (e.g., from consecutive video frames)
        using sequence matching to detect overlap.
        """
        if not segments:
            return []

        unique_segments = [segments[0]]

        for i in range(1, len(segments)):
            current = segments[i]
            previous = unique_segments[-1]

            if not current.strip():
                continue

            similarity = SequenceMatcher(None, previous, current).ratio()

            # If chunks are too similar, skip the current one
            # OR logic can be expanded to merge overlapping parts specifically
            if similarity < self.min_similarity:
                unique_segments.append(current)
            
        return unique_segments

    def merge_segments(self, segments: List[str]) -> str:
        """
        Joins cleaned and deduplicated segments into a single block.
        """
        return "\n".join(segments)

    def process_stream(self, raw_text_list: List[str]) -> str:
        """
        Pipeline: Clean -> Deduplicate -> Merge
        """
        cleaned = [self.clean_text(t) for t in raw_text_list]
        deduped = self.remove_duplicates(cleaned)
        return self.merge_segments(deduped)