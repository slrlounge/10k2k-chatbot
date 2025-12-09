"""
ChromaDB utility functions with retry logic and duplicate checking.
Ensures all ingestion uses remote ChromaDB HttpClient only.
"""

import os
import time
from typing import List, Dict, Optional, Tuple
from chromadb import HttpClient
from chromadb.errors import ChromaError
import hashlib


def get_chroma_client_with_retry(
    host: Optional[str] = None,
    port: Optional[int] = None,
    max_retries: int = 5,
    base_delay: float = 1.0
) -> HttpClient:
    """
    Create ChromaDB HttpClient with retry logic.
    Always uses remote HTTP client - never local storage.
    """
    host = host or os.getenv('CHROMA_HOST', 'chromadb-w5jr')
    port = port or int(os.getenv('CHROMA_PORT', '8000'))
    
    last_error = None
    for attempt in range(max_retries):
        try:
            client = HttpClient(host=host, port=port, ssl=False)
            # Test connection by listing collections
            client.list_collections()
            print(f"✓ Connected to remote ChromaDB at {host}:{port}")
            return client
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"⚠️  Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                print(f"✗ Failed to connect after {max_retries} attempts")
                raise RuntimeError(f"Failed to connect to ChromaDB at {host}:{port} after {max_retries} attempts: {last_error}")
    
    raise RuntimeError(f"Failed to connect to ChromaDB: {last_error}")


def get_collection_with_retry(
    client: HttpClient,
    collection_name: str,
    max_retries: int = 5,
    base_delay: float = 1.0
):
    """Get or create collection with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            try:
                collection = client.get_collection(collection_name)
                return collection
            except Exception:
                # Collection doesn't exist, create it
                collection = client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"✓ Created collection '{collection_name}'")
                return collection
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Collection operation attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Failed to get/create collection '{collection_name}' after {max_retries} attempts: {last_error}")
    
    raise RuntimeError(f"Failed to get/create collection: {last_error}")


def compute_chunk_hash(content: str, metadata: Dict) -> str:
    """Compute hash for duplicate detection."""
    # Create a stable hash from content and key metadata
    hash_input = f"{content}|{metadata.get('file_source', '')}|{metadata.get('section', '')}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def check_existing_chunks(
    collection,
    chunk_ids: List[str],
    max_retries: int = 5,
    base_delay: float = 1.0
) -> Tuple[List[str], List[int]]:
    """
    Check which chunks already exist in collection.
    Returns: (new_chunk_ids, existing_indices)
    """
    if not chunk_ids:
        return [], []
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Get existing IDs in batches
            existing_ids = set()
            batch_size = 100
            for i in range(0, len(chunk_ids), batch_size):
                batch_ids = chunk_ids[i:i+batch_size]
                try:
                    existing = collection.get(ids=batch_ids)
                    if existing and existing.get('ids'):
                        existing_ids.update(existing['ids'])
                except Exception:
                    # Batch doesn't exist, continue
                    pass
            
            # Find which chunks are new
            new_ids = []
            existing_indices = []
            for idx, chunk_id in enumerate(chunk_ids):
                if chunk_id not in existing_ids:
                    new_ids.append(chunk_id)
                else:
                    existing_indices.append(idx)
            
            return new_ids, existing_indices
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Duplicate check attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                # If duplicate check fails, assume all are new (safer to skip than duplicate)
                print(f"⚠️  Duplicate check failed, assuming all chunks are new")
                return chunk_ids, []
    
    return chunk_ids, []


def add_chunks_with_retry(
    collection,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict],
    batch_size: int = 10,
    max_retries: int = 5,
    base_delay: float = 1.0
) -> int:
    """
    Add chunks to collection with retry logic and duplicate checking.
    Returns: number of chunks actually added (excluding duplicates)
    """
    if not ids:
        return 0
    
    # Check for duplicates first
    new_ids, existing_indices = check_existing_chunks(collection, ids, max_retries, base_delay)
    
    if existing_indices:
        print(f"  ⚠️  Skipping {len(existing_indices)} duplicate chunk(s)")
    
    if not new_ids:
        print(f"  ℹ️  All chunks already exist, skipping insertion")
        return 0
    
    # Filter to only new chunks
    new_embeddings = []
    new_documents = []
    new_metadatas = []
    existing_set = set(existing_indices)
    
    for idx in range(len(ids)):
        if idx not in existing_set:
            new_embeddings.append(embeddings[idx])
            new_documents.append(documents[idx])
            new_metadatas.append(metadatas[idx])
    
    # Process in batches with retry
    total_added = 0
    for batch_start in range(0, len(new_ids), batch_size):
        batch_end = min(batch_start + batch_size, len(new_ids))
        batch_ids = new_ids[batch_start:batch_end]
        batch_embeddings = new_embeddings[batch_start:batch_end]
        batch_documents = new_documents[batch_start:batch_end]
        batch_metadatas = new_metadatas[batch_start:batch_end]
        
        last_error = None
        for attempt in range(max_retries):
            try:
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⚠️  Insert attempt {attempt + 1}/{max_retries} failed: {e}")
                    print(f"   Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"✗ Failed to insert batch after {max_retries} attempts: {last_error}")
                    raise RuntimeError(f"Failed to insert chunks after {max_retries} attempts: {last_error}")
    
    return total_added


def get_collection_count_with_retry(
    collection,
    max_retries: int = 5,
    base_delay: float = 1.0
) -> int:
    """Get collection count with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return collection.count()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise RuntimeError(f"Failed to get collection count after {max_retries} attempts: {last_error}")
    
    raise RuntimeError(f"Failed to get collection count: {last_error}")

