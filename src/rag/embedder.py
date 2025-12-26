"""Embedding generation module using sentence-transformers."""

from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np
from tqdm import tqdm


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""

    # Best multilingual models for Russian + English
    # DEFAULT_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'  # 384 dimensions, requires more RAM
    # DEFAULT_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'  # 384 dimensions
    # Lighter alternative for low-memory systems:
    DEFAULT_MODEL = 'cointegrated/rubert-tiny2'  # Russian, very light (~30MB), 312 dimensions

    def __init__(self, model_name: str = None):
        """
        Initialize embedding generator.

        Args:
            model_name: Name of sentence-transformers model
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        print(f"📥 Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"✅ Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def generate_embeddings(
        self,
        chunks: List[Dict],
        text_key: str = 'text',
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Generate embeddings for list of chunks.

        Args:
            chunks: List of chunk dictionaries
            text_key: Key in chunk dict containing text
            batch_size: Batch size for encoding
            show_progress: Show progress bar

        Returns:
            Chunks with added 'embedding' key
        """
        texts = [chunk[text_key] for chunk in chunks]

        print(f"\n🧠 Generating embeddings for {len(texts)} chunks...")

        # Generate embeddings with progress bar
        if show_progress:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
        else:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )

        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()  # Convert to list for JSON serialization

        print(f"✅ Generated {len(embeddings)} embeddings")

        return chunks

    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

        return float(similarity)

    def get_model_info(self) -> Dict:
        """Get information about loaded model."""
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'max_seq_length': self.model.max_seq_length
        }


if __name__ == "__main__":
    # Test embedder
    from chunker import TextChunker

    print("🧪 Testing EmbeddingGenerator\n")

    # Sample text
    sample_chunks = [
        {'text': 'Привычки - это маленькие решения, которые мы принимаем каждый день.', 'index': 0},
        {'text': 'Изменение привычек требует времени и последовательности.', 'index': 1},
        {'text': 'Habits are the compound interest of self-improvement.', 'index': 2}
    ]

    # Initialize embedder
    embedder = EmbeddingGenerator()

    # Get model info
    info = embedder.get_model_info()
    print(f"📊 Model Info:")
    print(f"   Name: {info['model_name']}")
    print(f"   Dimension: {info['embedding_dimension']}")
    print(f"   Max length: {info['max_seq_length']}\n")

    # Generate embeddings
    chunks_with_embeddings = embedder.generate_embeddings(sample_chunks)

    print(f"\n✅ Generated embeddings:")
    for chunk in chunks_with_embeddings:
        print(f"   Chunk {chunk['index']}: {len(chunk['embedding'])} dimensions")
        print(f"   First 5 values: {chunk['embedding'][:5]}\n")

    # Test similarity
    emb1 = chunks_with_embeddings[0]['embedding']
    emb2 = chunks_with_embeddings[1]['embedding']
    emb3 = chunks_with_embeddings[2]['embedding']

    sim_ru_ru = embedder.cosine_similarity(emb1, emb2)
    sim_ru_en = embedder.cosine_similarity(emb1, emb3)

    print(f"📏 Similarity scores:")
    print(f"   Russian-Russian: {sim_ru_ru:.4f}")
    print(f"   Russian-English: {sim_ru_en:.4f}")
