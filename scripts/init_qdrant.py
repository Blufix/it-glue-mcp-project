#!/usr/bin/env python3
"""Initialize Qdrant vector database collections."""

import asyncio
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    CollectionInfo,
    OptimizersConfigDiff,
    HnswConfigDiff
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings


def init_qdrant():
    """Initialize Qdrant collections for IT Glue embeddings."""
    
    print("Initializing Qdrant collections...")
    print("-" * 50)
    
    # Connect to Qdrant
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        https=False
    )
    
    collections_config = [
        {
            "name": "itglue_documents",
            "vector_size": 384,  # all-MiniLM-L6-v2 dimension
            "distance": Distance.COSINE,
            "description": "IT Glue documentation embeddings"
        },
        {
            "name": "itglue_configurations",
            "vector_size": 384,
            "distance": Distance.COSINE,
            "description": "IT Glue configuration embeddings"
        },
        {
            "name": "itglue_passwords",
            "vector_size": 384,
            "distance": Distance.COSINE,
            "description": "IT Glue password metadata embeddings (no actual passwords)"
        },
        {
            "name": "itglue_flexible_assets",
            "vector_size": 384,
            "distance": Distance.COSINE,
            "description": "IT Glue flexible asset embeddings"
        },
        {
            "name": "itglue_contacts",
            "vector_size": 384,
            "distance": Distance.COSINE,
            "description": "IT Glue contact embeddings"
        }
    ]
    
    for config in collections_config:
        collection_name = config["name"]
        
        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name)
            print(f"✓ Collection '{collection_name}' already exists with {collection_info.points_count} points")
            
            # Optionally recreate for clean state
            # print(f"  Recreating collection '{collection_name}'...")
            # client.delete_collection(collection_name)
            # raise Exception("Recreate")
            
        except Exception:
            # Create collection
            print(f"Creating collection '{collection_name}'...")
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=config["vector_size"],
                    distance=config["distance"]
                ),
                # Optimize for performance
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000,
                    memmap_threshold=50000
                ),
                # HNSW index configuration for fast search
                hnsw_config=HnswConfigDiff(
                    m=16,  # Number of connections
                    ef_construct=100,  # Build-time accuracy
                    full_scan_threshold=10000
                )
            )
            
            print(f"✅ Collection '{collection_name}' created successfully")
    
    # Create unified search collection for cross-entity searches
    unified_collection = "itglue_unified"
    try:
        collection_info = client.get_collection(unified_collection)
        print(f"✓ Unified collection already exists with {collection_info.points_count} points")
    except Exception:
        print(f"Creating unified collection '{unified_collection}'...")
        
        client.create_collection(
            collection_name=unified_collection,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=50000,
                memmap_threshold=100000
            ),
            hnsw_config=HnswConfigDiff(
                m=32,  # More connections for larger dataset
                ef_construct=200,
                full_scan_threshold=20000
            )
        )
        
        print(f"✅ Unified collection created successfully")
    
    # List all collections
    print("\n" + "=" * 50)
    print("Current Qdrant collections:")
    collections = client.get_collections()
    for collection in collections.collections:
        info = client.get_collection(collection.name)
        print(f"  • {collection.name}: {info.points_count} vectors, status={info.status}")
    
    print("-" * 50)
    print("Qdrant initialization complete!")
    
    return client


if __name__ == "__main__":
    init_qdrant()