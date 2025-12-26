"""RAG search engine using ChromaDB for vector storage and retrieval."""

import sys
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class RAGSearchEngine:
    """Vector search engine for RAG using ChromaDB."""

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "james_clear_atomic_habits"
    ):
        """
        Initialize RAG search engine.

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Book chunks with embeddings"}
        )

        print(f"✅ ChromaDB initialized at: {persist_directory}")
        print(f"   Collection: {collection_name}")
        print(f"   Current documents: {self.collection.count()}")

    def add_chunks(
        self,
        chunks: List[Dict],
        embeddings: List[List[float]] = None
    ) -> None:
        """
        Add chunks to the vector database.

        Args:
            chunks: List of chunk dictionaries
            embeddings: Pre-computed embeddings (optional, will use chunk['embedding'])
        """
        if not chunks:
            print("⚠️  No chunks to add")
            return

        # Prepare data for ChromaDB
        import uuid
        # Generate unique IDs using UUID to avoid duplicates
        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [chunk['text'] for chunk in chunks]

        # Use provided embeddings or extract from chunks
        if embeddings is None:
            if 'embedding' not in chunks[0]:
                raise ValueError("Chunks must have 'embedding' key or provide embeddings parameter")
            embeddings = [chunk['embedding'] for chunk in chunks]

        # Prepare metadata
        metadatas = []
        for chunk in chunks:
            metadata = {
                'char_count': chunk.get('char_count', 0),
                'word_count': chunk.get('word_count', 0),
                'index': chunk.get('index', 0)
            }

            # Add custom metadata if exists
            if 'metadata' in chunk:
                metadata.update(chunk['metadata'])

            metadatas.append(metadata)

        # Add to collection
        print(f"📤 Adding {len(chunks)} chunks to ChromaDB...")

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        print(f"✅ Added {len(chunks)} chunks")
        print(f"   Total documents in collection: {self.collection.count()}")

    def search(
        self,
        query: str,
        query_embedding: List[float] = None,
        n_results: int = 3,
        where: Dict = None
    ) -> List[Dict]:
        """
        Search for relevant chunks.

        Args:
            query: Search query text
            query_embedding: Pre-computed query embedding (optional)
            n_results: Number of results to return
            where: Metadata filter (optional)

        Returns:
            List of relevant chunks with similarity scores
        """
        # Search using query embedding
        if query_embedding:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
        else:
            # Let ChromaDB handle embedding generation
            # Note: This requires default_ef embedding function
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

        # Format results
        formatted_results = []

        for i in range(len(results['ids'][0])):
            result = {
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            }
            formatted_results.append(result)

        return formatted_results

    def search_with_embedder(
        self,
        query: str,
        embedder,
        n_results: int = 3,
        where: Dict = None
    ) -> List[Dict]:
        """
        Search using external embedder (sentence-transformers).

        Args:
            query: Search query
            embedder: EmbeddingGenerator instance
            n_results: Number of results
            where: Metadata filter

        Returns:
            List of relevant chunks
        """
        # Generate query embedding
        query_embedding = embedder.generate_single_embedding(query)

        # Search
        return self.search(
            query=query,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where
        )

    def get_stats(self) -> Dict:
        """Get collection statistics."""
        count = self.collection.count()

        stats = {
            'collection_name': self.collection_name,
            'total_documents': count,
            'persist_directory': self.persist_directory
        }

        return stats

    def clear_collection(self) -> None:
        """Clear all documents from collection."""
        # Delete and recreate collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Book chunks with embeddings"}
        )
        print(f"🗑️  Cleared collection: {self.collection_name}")


if __name__ == "__main__":
    # Test RAG search
    print("🧪 Testing RAGSearchEngine\n")

    # Initialize search engine
    search_engine = RAGSearchEngine(
        persist_directory="./test_chroma_db",
        collection_name="test_collection"
    )

    # Clear for clean test
    search_engine.clear_collection()

    # Sample chunks with embeddings
    sample_chunks = [
        {
            'text': 'Привычки - это маленькие решения, которые мы принимаем каждый день.',
            'index': 0,
            'char_count': 65,
            'word_count': 10,
            'embedding': [0.1] * 384,  # Dummy embedding
            'metadata': {'chapter': 'Введение'}
        },
        {
            'text': 'Изменение привычек требует времени и последовательности.',
            'index': 1,
            'char_count': 55,
            'word_count': 6,
            'embedding': [0.2] * 384,
            'metadata': {'chapter': 'Глава 1'}
        }
    ]

    # Add chunks
    search_engine.add_chunks(sample_chunks)

    # Get stats
    stats = search_engine.get_stats()
    print(f"\n📊 Collection Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ RAGSearchEngine test completed!")
