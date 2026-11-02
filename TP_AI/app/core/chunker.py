from typing import List, Dict, Any, Optional
import re
from app.config import settings


class TextChunker:
    """Intelligent recursive text chunker for segmenting documents before embedding."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Split text recursively by separators into chunks satisfying chunk_size and chunk_overlap."""
        text = text.strip()
        if not text:
            return []
        
        if len(text) <= self.chunk_size:
            return [text]

        return self._recursive_split(text, self.separators)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks = []
        separator = separators[-1]
        new_separators = []

        for i, _s in enumerate(separators):
            if _s == "":
                separator = _s
                break
            if _s in text:
                separator = _s
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator != "" else list(text)
        
        good_splits = []
        for s in splits:
            if separator and s:
                good_splits.append(s)
            elif not separator:
                good_splits.append(s)

        current_chunk = []
        current_len = 0

        for s in good_splits:
            s_len = len(s) + (len(separator) if separator else 0)
            if current_len + s_len > self.chunk_size and current_chunk:
                merged = separator.join(current_chunk).strip()
                if merged:
                    final_chunks.append(merged)
                
                # Apply overlap: keep the last few pieces if possible
                overlap_chunk = []
                overlap_len = 0
                for prev in reversed(current_chunk):
                    if overlap_len + len(prev) <= self.chunk_overlap:
                        overlap_chunk.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_len = sum(len(x) for x in current_chunk) + (len(separator) * max(0, len(current_chunk) - 1))

            current_chunk.append(s)
            current_len += len(s) + (len(separator) if len(current_chunk) > 1 else 0)

        if current_chunk:
            merged = separator.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        # If any chunk is still larger than chunk_size and we have deeper separators, split it further
        processed_chunks = []
        for chunk in final_chunks:
            if len(chunk) > self.chunk_size and new_separators:
                processed_chunks.extend(self._recursive_split(chunk, new_separators))
            else:
                processed_chunks.append(chunk)

        return processed_chunks

    def chunk_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Splits document content into chunk dictionaries with metadata and chunk indices."""
        chunks = self.split_text(content)
        result = []
        
        for idx, chunk in enumerate(chunks):
            chunk_meta = (metadata or {}).copy()
            chunk_meta.update({
                "chunk_index": idx,
                "total_chunks": len(chunks),
            })
            result.append({
                "chunk_index": idx,
                "content": chunk,
                "metadata": chunk_meta,
            })
        return result


text_chunker = TextChunker()
