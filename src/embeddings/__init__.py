"""Embedding generation and management."""

from .generator import EmbeddingGenerator, ChunkProcessor
from .manager import EmbeddingManager

__all__ = [
    'EmbeddingGenerator',
    'ChunkProcessor',
    'EmbeddingManager'
]