# Embeddings Configuration

## Critical Embedding Model Setup

The IT Glue MCP Server uses **nomic-embed-text** as the primary embedding model for semantic search. This configuration is critical for system functionality.

## Model Specifications

- **Model**: `nomic-embed-text`
- **Dimensions**: `768`
- **Provider**: Ollama (local inference)
- **Distance**: Cosine similarity

## Key Configuration Requirements

### 1. Embedding Generator (`src/embeddings/generator.py`)
- Default model: `"nomic-embed-text"`
- Default dimension: `768`
- Ollama endpoint: Configured via `settings.ollama_url`

```python
# CRITICAL: Default to nomic-embed-text for consistency
model_name: str = "nomic-embed-text"
self.dimension = 768  # nomic-embed-text dimensions - CRITICAL: Ollama model
```

### 2. Qdrant Vector Database
- Collection name: `itglue_entities`
- Vector size: `768` dimensions
- Distance metric: `COSINE`

### 3. Ollama Configuration
- Required model: `nomic-embed-text`
- API endpoint: `http://localhost:11434`

## Why nomic-embed-text?

1. **High Quality**: Nomic's embedding model provides superior semantic understanding
2. **Local Inference**: Runs entirely on local hardware via Ollama
3. **Privacy**: No external API calls for embeddings
4. **Consistency**: 768-dimensional vectors provide stable results

## Architecture Flow

```
IT Glue Data → EmbeddingGenerator → nomic-embed-text (768D) → Qdrant Collection
                                                                      ↓
User Query → EmbeddingGenerator → nomic-embed-text (768D) → Semantic Search
```

## Implementation Status

✅ **Active**: All components configured for nomic-embed-text
✅ **Data**: 102 Faucets entities embedded with 768 dimensions  
✅ **Search**: Semantic search operational with keyword + vector hybrid
✅ **Performance**: Sub-2 second response times for semantic queries

## Configuration Files

- `src/embeddings/generator.py`: Embedding model defaults
- `src/search/semantic.py`: Qdrant vector operations
- `src/search/unified_hybrid.py`: Hybrid search integration
- `.env`: Ollama endpoint configuration

## Troubleshooting

### Common Issues

1. **Dimension Mismatch (400 Bad Request)**
   - Cause: Vector dimension inconsistency
   - Solution: Ensure all components use 768D nomic-embed-text

2. **Model Not Found**
   - Cause: Ollama doesn't have nomic-embed-text installed
   - Solution: `ollama pull nomic-embed-text`

3. **Empty Embeddings**
   - Cause: Ollama service not running
   - Solution: `ollama serve` or check Docker containers

### Verification Commands

```bash
# Test embedding generation
poetry run python tests/scripts/generate_embeddings_nomic.py

# Test semantic search
poetry run python test_semantic_search_direct.py

# Check Ollama models
ollama list
```

## Migration Notes

If switching between embedding models:

1. **Delete existing Qdrant collection** (dimension changes require recreation)
2. **Regenerate all embeddings** with new model
3. **Update all EmbeddingGenerator instances** to use new model
4. **Test semantic search functionality**

## Performance Metrics

- **Embedding Generation**: ~50ms per text chunk (local inference)
- **Vector Search**: <100ms for similarity queries
- **Batch Processing**: 50 texts per batch for optimal throughput
- **Storage**: ~3KB per 768D vector in Qdrant