"""Script to ingest EPUB book into RAG system."""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.rag.epub_parser import EPUBParser
from src.rag.chunker import TextChunker
from src.rag.embedder import EmbeddingGenerator
from src.rag.search import RAGSearchEngine


def ingest_book(
    epub_path: str,
    collection_name: str = "james_clear_atomic_habits",
    chunk_size: int = 800,
    chunk_overlap: int = 200,
    persist_directory: str = "./data/chroma_db"
):
    """
    Complete pipeline to ingest a book into RAG system.

    Args:
        epub_path: Path to EPUB file
        collection_name: Name for ChromaDB collection
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        persist_directory: Where to store ChromaDB data
    """
    print("=" * 60)
    print("📚 BOOK INGESTION PIPELINE")
    print("=" * 60)

    # Step 1: Parse EPUB
    print("\n[1/5] 📖 Parsing EPUB...")
    parser = EPUBParser(epub_path)

    # Get metadata
    metadata = parser.get_metadata()
    print(f"\n📄 Book Info:")
    print(f"   Title: {metadata['title']}")
    print(f"   Author: {metadata['author']}")
    print(f"   Language: {metadata['language']}")

    # Extract chapters
    chapters = parser.extract_chapters()
    print(f"\n✅ Extracted {len(chapters)} chapters")

    # Step 2: Chunk text
    print(f"\n[2/5] 🔪 Chunking text...")
    print(f"   Chunk size: {chunk_size} chars")
    print(f"   Overlap: {chunk_overlap} chars")

    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = chunker.chunk_by_chapters(chapters)
    print(f"\n✅ Created {len(chunks)} chunks")

    # Show stats
    total_chars = sum(chunk['char_count'] for chunk in chunks)
    total_words = sum(chunk['word_count'] for chunk in chunks)
    avg_chunk_size = total_chars / len(chunks) if chunks else 0

    print(f"\n📊 Chunk Statistics:")
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Total characters: {total_chars:,}")
    print(f"   Total words: {total_words:,}")
    print(f"   Average chunk size: {avg_chunk_size:.0f} chars")

    # Step 3: Generate embeddings
    print(f"\n[3/5] 🧠 Generating embeddings...")

    embedder = EmbeddingGenerator()

    chunks_with_embeddings = embedder.generate_embeddings(
        chunks,
        batch_size=4,  # Small batch for low-memory systems
        show_progress=True
    )

    # Add book metadata to each chunk
    for chunk in chunks_with_embeddings:
        if 'metadata' not in chunk:
            chunk['metadata'] = {}
        chunk['metadata']['book_title'] = metadata['title']
        chunk['metadata']['author'] = metadata['author']

    # Step 4: Initialize ChromaDB
    print(f"\n[4/5] 🗄️  Setting up ChromaDB...")

    search_engine = RAGSearchEngine(
        persist_directory=persist_directory,
        collection_name=collection_name
    )

    # Clear existing data for this collection (optional)
    if search_engine.collection.count() > 0:
        response = input(f"\n⚠️  Collection already has {search_engine.collection.count()} documents. Clear it? (y/n): ")
        if response.lower() == 'y':
            search_engine.clear_collection()
            print("🗑️  Cleared existing data")

    # Step 5: Add to ChromaDB
    print(f"\n[5/5] 📤 Adding chunks to ChromaDB...")

    search_engine.add_chunks(chunks_with_embeddings)

    # Final stats
    stats = search_engine.get_stats()

    print("\n" + "=" * 60)
    print("✅ INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\n📊 Final Statistics:")
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Documents: {stats['total_documents']}")
    print(f"   Storage: {stats['persist_directory']}")

    # Test search
    print(f"\n🔍 Testing search...")
    test_query = "Как сформировать привычку?"

    results = search_engine.search_with_embedder(
        test_query,
        embedder,
        n_results=3
    )

    print(f"\n📝 Search results for: '{test_query}'")
    for i, result in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Chapter: {result['metadata'].get('chapter_title', 'Unknown')}")
        print(f"   Text: {result['text'][:200]}...")
        if result['distance']:
            print(f"   Distance: {result['distance']:.4f}")

    print("\n" + "=" * 60)
    print("🎉 All done! RAG system is ready to use.")
    print("=" * 60)


if __name__ == "__main__":
    # Default book path
    default_book = "./data/books/Джеймс_Клир_Атомные_привычки_Как_приобрести_хорошие_привычки.epub"

    # Get book path from command line or use default
    if len(sys.argv) > 1:
        book_path = sys.argv[1]
    else:
        book_path = default_book

    # Check if file exists
    if not os.path.exists(book_path):
        print(f"❌ Error: Book not found at {book_path}")
        print(f"\nUsage: python ingest_book.py [path_to_epub]")
        sys.exit(1)

    # Run ingestion
    ingest_book(
        epub_path=book_path,
        collection_name="james_clear_atomic_habits",
        chunk_size=800,  # ~500-600 words
        chunk_overlap=200
    )
