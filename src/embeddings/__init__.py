"""Embedding generation and management."""

from .generator import ChunkProcessor, EmbeddingGenerator
from .manager import EmbeddingManager

__all__ = [
    'EmbeddingGenerator',
    'ChunkProcessor',
    'EmbeddingManager'
]
