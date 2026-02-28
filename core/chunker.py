import math
from typing import List, Tuple
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    def __init__(self, max_chunk_size: int = 2000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    def chunk_text(self, text: str) -> List[Tuple[int, str]]:
        """
        Split text into overlapping chunks with proper sentence boundary preservation
        Returns list of tuples (chunk_index, chunk_content)
        """
        if not text or len(text.strip()) == 0:
            return [(0, "")]

        # Split text into sentences to preserve sentence boundaries
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed the chunk size
            if current_length + sentence_length > self.max_chunk_size:
                # If the sentence itself is too long, split it
                if sentence_length > self.max_chunk_size:
                    subchunks = self._split_long_sentence(sentence)
                    for subchunk in subchunks:
                        if len(subchunk) <= self.max_chunk_size:
                            chunks.append((chunk_index, subchunk))
                            chunk_index += 1
                        else:
                            # If still too long, force split by character
                            forced_chunks = self._force_split_by_size(subchunk)
                            for fc in forced_chunks:
                                chunks.append((chunk_index, fc))
                                chunk_index += 1
                else:
                    # Add current chunk to list and start a new one
                    if current_chunk.strip():
                        chunks.append((chunk_index, current_chunk.strip()))
                        chunk_index += 1
                    
                    # Start new chunk with overlap from previous chunk
                    if self.overlap_size > 0 and chunks:
                        # Get the tail of the previous chunk to use as overlap
                        prev_chunk = chunks[-1][1]
                        overlap_part = self._get_overlap(prev_chunk)
                        current_chunk = overlap_part + " " + sentence
                        current_length = len(current_chunk)
                    else:
                        current_chunk = sentence
                        current_length = sentence_length
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_length += sentence_length + 1  # +1 for space
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append((chunk_index, current_chunk.strip()))
        
        logger.info(f"Text split into {len(chunks)} chunks")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using punctuation marks
        """
        import re
        # This regex handles common sentence endings while preserving abbreviations
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, text)
        # Filter out empty strings and strip whitespace
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """
        Split a sentence that is too long for a chunk
        """
        words = sentence.split()
        subchunks = []
        current_subchunk = ""
        
        for word in words:
            if len(current_subchunk + " " + word) <= self.max_chunk_size:
                if current_subchunk:
                    current_subchunk += " " + word
                else:
                    current_subchunk = word
            else:
                if current_subchunk:  # Don't add empty chunks
                    subchunks.append(current_subchunk)
                current_subchunk = word
        
        if current_subchunk:  # Add the last subchunk
            subchunks.append(current_subchunk)
        
        return subchunks
    
    def _force_split_by_size(self, text: str) -> List[str]:
        """
        Force split text by character count when other methods fail
        """
        chunks = []
        for i in range(0, len(text), self.max_chunk_size):
            chunk = text[i:i + self.max_chunk_size]
            chunks.append(chunk)
        return chunks
    
    def _get_overlap(self, chunk: str) -> str:
        """
        Get the ending portion of a chunk to use as overlap
        """
        words = chunk.split()
        # Take the last few words as overlap, up to overlap_size characters
        overlap_words = []
        overlap_chars = 0
        
        for word in reversed(words):
            if overlap_chars + len(word) <= self.overlap_size:
                overlap_words.insert(0, word)
                overlap_chars += len(word) + 1
            else:
                break
        
        return " ".join(overlap_words)
    
    def calculate_token_estimate(self, text: str) -> int:
        """
        Estimate the number of tokens in text (rough approximation)
        1 token ≈ 4 characters or 0.75 words
        """
        # Rough estimate: divide character count by 4
        return math.ceil(len(text) / 4)
    
    def chunk_with_token_limit(self, text: str, max_tokens: int) -> List[Tuple[int, str]]:
        """
        Split text into chunks respecting token limits
        """
        # First, do a rough split based on character count
        estimated_tokens = self.calculate_token_estimate(text)
        approx_chunks_needed = math.ceil(estimated_tokens / max_tokens)
        approx_chunk_size = len(text) // approx_chunks_needed
        
        # Now do the actual chunking with the calculated size
        chunks = []
        chunk_index = 0
        
        for i in range(0, len(text), approx_chunk_size):
            chunk = text[i:i + approx_chunk_size]
            chunks.append((chunk_index, chunk))
            chunk_index += 1
        
        return chunks