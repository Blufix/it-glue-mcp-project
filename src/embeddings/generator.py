"""Embedding generation using Ollama and OpenAI."""

import logging
from typing import List, Optional, Dict, Any
import numpy as np
import aiohttp
import asyncio
from sentence_transformers import SentenceTransformer
import torch

from src.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for text using various models."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        ollama_url: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize embedding generator.
        
        Args:
            model_name: Model to use for embeddings
            ollama_url: Ollama API URL for local generation
            openai_api_key: OpenAI API key for fallback
        """
        self.model_name = model_name
        self.ollama_url = ollama_url or settings.ollama_url
        self.openai_api_key = openai_api_key or settings.openai_api_key
        
        # Initialize local model if available
        self.local_model = None
        try:
            self.local_model = SentenceTransformer(model_name)
            logger.info(f"Loaded local model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load local model {model_name}: {e}")
            
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        
    async def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        embeddings = None
        
        # Try local model first
        if self.local_model:
            try:
                embeddings = await self._generate_local(texts)
                logger.debug(f"Generated {len(embeddings)} embeddings locally")
            except Exception as e:
                logger.warning(f"Local embedding generation failed: {e}")
                
        # Try Ollama if local failed
        if embeddings is None and self.ollama_url:
            try:
                embeddings = await self._generate_ollama(texts)
                logger.debug(f"Generated {len(embeddings)} embeddings with Ollama")
            except Exception as e:
                logger.warning(f"Ollama embedding generation failed: {e}")
                
        # Try OpenAI as fallback
        if embeddings is None and self.openai_api_key:
            try:
                embeddings = await self._generate_openai(texts)
                logger.debug(f"Generated {len(embeddings)} embeddings with OpenAI")
                self.dimension = 1536  # OpenAI ada-002 dimension
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {e}")
                raise RuntimeError("All embedding generation methods failed")
                
        if embeddings is None:
            raise RuntimeError("No embedding generation method available")
            
        # Normalize if requested
        if normalize:
            embeddings = self._normalize_embeddings(embeddings)
            
        return embeddings
        
    async def _generate_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model.
        
        Args:
            texts: Texts to embed
            
        Returns:
            Embedding vectors
        """
        if not self.local_model:
            raise RuntimeError("Local model not available")
            
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.local_model.encode,
            texts
        )
        
        return embeddings.tolist()
        
    async def _generate_ollama(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama.
        
        Args:
            texts: Texts to embed
            
        Returns:
            Embedding vectors
        """
        if not self.ollama_url:
            raise RuntimeError("Ollama URL not configured")
            
        embeddings = []
        
        async with aiohttp.ClientSession() as session:
            for text in texts:
                data = {
                    "model": "all-minilm",
                    "prompt": text
                }
                
                async with session.post(
                    f"{self.ollama_url}/api/embeddings",
                    json=data
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(
                            f"Ollama returned status {response.status}"
                        )
                        
                    result = await response.json()
                    embeddings.append(result["embedding"])
                    
        return embeddings
        
    async def _generate_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI.
        
        Args:
            texts: Texts to embed
            
        Returns:
            Embedding vectors
        """
        if not self.openai_api_key:
            raise RuntimeError("OpenAI API key not configured")
            
        embeddings = []
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Batch process texts
            for i in range(0, len(texts), 100):
                batch = texts[i:i + 100]
                
                data = {
                    "model": "text-embedding-ada-002",
                    "input": batch
                }
                
                async with session.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise RuntimeError(f"OpenAI API error: {error}")
                        
                    result = await response.json()
                    
                    for item in result["data"]:
                        embeddings.append(item["embedding"])
                        
        return embeddings
        
    def _normalize_embeddings(
        self,
        embeddings: List[List[float]]
    ) -> List[List[float]]:
        """Normalize embeddings for cosine similarity.
        
        Args:
            embeddings: Raw embeddings
            
        Returns:
            Normalized embeddings
        """
        normalized = []
        
        for embedding in embeddings:
            # Convert to numpy array
            vec = np.array(embedding)
            
            # Normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
                
            normalized.append(vec.tolist())
            
        return normalized
        
    async def generate_batch(
        self,
        texts: List[str],
        batch_size: int = 50,
        normalize: bool = True
    ) -> List[List[float]]:
        """Generate embeddings in batches.
        
        Args:
            texts: Texts to embed
            batch_size: Size of each batch
            normalize: Whether to normalize
            
        Returns:
            All embeddings
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                embeddings = await self.generate_embeddings(batch, normalize)
                all_embeddings.extend(embeddings)
                
                logger.debug(
                    f"Processed batch {i // batch_size + 1}: "
                    f"{len(batch)} texts"
                )
                
            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                # Add empty embeddings for failed batch
                all_embeddings.extend([[0.0] * self.dimension] * len(batch))
                
        return all_embeddings
        
    def get_dimension(self) -> int:
        """Get embedding dimension.
        
        Returns:
            Embedding vector dimension
        """
        return self.dimension


class ChunkProcessor:
    """Processes text into chunks for embedding."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """Initialize chunk processor.
        
        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
            
        chunks = []
        
        # Simple character-based chunking
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk_text = text[i:i + self.chunk_size]
            
            chunks.append({
                "text": chunk_text,
                "start": i,
                "end": min(i + self.chunk_size, len(text))
            })
            
        return chunks
        
    def chunk_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Chunk multiple documents.
        
        Args:
            documents: List of documents with 'text' field
            
        Returns:
            List of chunks with document metadata
        """
        all_chunks = []
        
        for doc in documents:
            text = doc.get("text", "")
            doc_id = doc.get("id", "")
            
            chunks = self.chunk_text(text)
            
            for chunk in chunks:
                chunk["document_id"] = doc_id
                chunk["metadata"] = doc.get("metadata", {})
                all_chunks.append(chunk)
                
        return all_chunks