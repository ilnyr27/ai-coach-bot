"""EPUB book parser for extracting clean text."""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict
import re


class EPUBParser:
    """Parse EPUB books and extract clean text."""

    def __init__(self, epub_path: str):
        """
        Initialize EPUB parser.

        Args:
            epub_path: Path to EPUB file
        """
        self.epub_path = epub_path
        self.book = None
        self.chapters = []

    def load(self) -> None:
        """Load EPUB file."""
        try:
            self.book = epub.read_epub(self.epub_path)
            print(f"✅ Loaded EPUB: {self.epub_path}")
        except Exception as e:
            raise Exception(f"❌ Failed to load EPUB: {e}")

    def extract_text(self) -> str:
        """
        Extract all text from EPUB.

        Returns:
            Complete book text as string
        """
        if not self.book:
            self.load()

        full_text = []

        # Iterate through all items in the book
        for item in self.book.get_items():
            # Only process document items (chapters)
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse HTML content
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up whitespace
                text = self._clean_text(text)

                if text.strip():  # Only add non-empty chapters
                    full_text.append(text)

        return '\n\n'.join(full_text)

    def extract_chapters(self) -> List[Dict[str, str]]:
        """
        Extract text by chapters.

        Returns:
            List of dicts with chapter title and text
        """
        if not self.book:
            self.load()

        chapters = []
        chapter_num = 0

        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # Try to get chapter title
                title = None
                for heading in soup.find_all(['h1', 'h2', 'h3']):
                    if heading.get_text().strip():
                        title = heading.get_text().strip()
                        break

                if not title:
                    title = f"Chapter {chapter_num + 1}"

                # Remove scripts and styles
                for script in soup(["script", "style"]):
                    script.decompose()

                text = soup.get_text()
                text = self._clean_text(text)

                if text.strip():
                    chapters.append({
                        'title': title,
                        'text': text,
                        'chapter_num': chapter_num
                    })
                    chapter_num += 1

        self.chapters = chapters
        return chapters

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    def get_metadata(self) -> Dict[str, str]:
        """
        Extract book metadata.

        Returns:
            Dictionary with title, author, etc.
        """
        if not self.book:
            self.load()

        metadata = {}

        # Get title
        title = self.book.get_metadata('DC', 'title')
        metadata['title'] = title[0][0] if title else 'Unknown'

        # Get author
        creator = self.book.get_metadata('DC', 'creator')
        metadata['author'] = creator[0][0] if creator else 'Unknown'

        # Get language
        language = self.book.get_metadata('DC', 'language')
        metadata['language'] = language[0][0] if language else 'Unknown'

        return metadata


if __name__ == "__main__":
    # Test parser
    import sys

    if len(sys.argv) > 1:
        epub_path = sys.argv[1]
    else:
        epub_path = "../data/books/Джеймс_Клир_Атомные_привычки_Как_приобрести_хорошие_привычки.epub"

    parser = EPUBParser(epub_path)

    # Get metadata
    metadata = parser.get_metadata()
    print(f"\n📖 Book Metadata:")
    print(f"  Title: {metadata['title']}")
    print(f"  Author: {metadata['author']}")
    print(f"  Language: {metadata['language']}")

    # Extract chapters
    chapters = parser.extract_chapters()
    print(f"\n📚 Found {len(chapters)} chapters")

    # Show first chapter preview
    if chapters:
        first_chapter = chapters[0]
        print(f"\n📄 First chapter: {first_chapter['title']}")
        print(f"   Preview: {first_chapter['text'][:200]}...")
        print(f"   Length: {len(first_chapter['text'])} characters")
