"""Text chunking module for splitting text into manageable pieces."""

from typing import List, Dict
import re


class TextChunker:
    """Split text into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            separator: Primary separator to use (paragraph breaks)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into chunks.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Split by separator first (paragraphs)
        paragraphs = text.split(self.separator)

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph exceeds chunk_size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk,
                        chunk_index,
                        metadata
                    ))
                    chunk_index += 1

                    # Start new chunk with overlap
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = overlap_text + paragraph
                else:
                    # Paragraph is too long, split it by sentences
                    if len(paragraph) > self.chunk_size:
                        sentence_chunks = self._split_long_paragraph(paragraph)
                        for sent_chunk in sentence_chunks:
                            chunks.append(self._create_chunk(
                                sent_chunk,
                                chunk_index,
                                metadata
                            ))
                            chunk_index += 1
                    else:
                        current_chunk = paragraph
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += self.separator + paragraph
                else:
                    current_chunk = paragraph

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk,
                chunk_index,
                metadata
            ))

        return chunks

    def _create_chunk(
        self,
        text: str,
        index: int,
        metadata: Dict = None
    ) -> Dict:
        """Create chunk dictionary."""
        chunk = {
            'text': text.strip(),
            'index': index,
            'char_count': len(text),
            'word_count': len(text.split())
        }

        if metadata:
            chunk['metadata'] = metadata

        return chunk

    def _get_overlap(self, text: str) -> str:
        """Get overlap text from end of chunk."""
        if len(text) <= self.chunk_overlap:
            return text

        # Try to find last sentence in overlap region
        overlap_text = text[-self.chunk_overlap:]

        # Find last sentence boundary
        sentences = re.split(r'[.!?]\s+', overlap_text)
        if len(sentences) > 1:
            # Use last complete sentence
            return sentences[-1] + self.separator
        else:
            # No sentence boundary, just use the text
            return overlap_text + self.separator

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """Split a paragraph that's longer than chunk_size."""
        # Split by sentences
        sentences = re.split(r'([.!?]\s+)', paragraph)

        # Rejoin sentence with its punctuation
        sentences = [
            sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
            for i in range(0, len(sentences), 2)
        ]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_chapters(
        self,
        chapters: List[Dict],
        metadata_key: str = 'title'
    ) -> List[Dict]:
        """
        Chunk text by chapters, preserving chapter information.

        Args:
            chapters: List of chapter dicts from EPUBParser
            metadata_key: Key in chapter dict to use for metadata

        Returns:
            List of chunks with chapter metadata
        """
        all_chunks = []

        for chapter in chapters:
            chapter_text = chapter.get('text', '')
            chapter_metadata = {
                'chapter_title': chapter.get(metadata_key, ''),
                'chapter_num': chapter.get('chapter_num', 0)
            }

            chapter_chunks = self.chunk_text(chapter_text, chapter_metadata)
            all_chunks.extend(chapter_chunks)

        return all_chunks


if __name__ == "__main__":
    # Test chunker
    sample_text = """
    Это первый параграф. Он содержит несколько предложений. Это важно для тестирования.

    Это второй параграф. Он тоже содержит текст. Давайте проверим как работает chunking.

    Третий параграф здесь. Chunker должен разбить этот текст на куски примерно по 100 символов.

    Четвертый параграф для теста. Система должна сохранять контекст между чанками.
    """

    chunker = TextChunker(chunk_size=150, chunk_overlap=50)
    chunks = chunker.chunk_text(sample_text)

    print(f"📝 Created {len(chunks)} chunks:\n")
    for chunk in chunks:
        print(f"Chunk {chunk['index']}:")
        print(f"  Text: {chunk['text'][:100]}...")
        print(f"  Words: {chunk['word_count']}, Chars: {chunk['char_count']}\n")
