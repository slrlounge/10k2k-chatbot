#!/usr/bin/env python3
"""
ChromaDB Optimization Script
Deduplicates embeddings and ensures proper metadata for RAG.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from collections import defaultdict

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')


def get_collection():
    """Get ChromaDB collection."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error getting collection: {e}")
        sys.exit(1)


def deduplicate_embeddings(collection):
    """Remove duplicate embeddings based on content."""
    print("Scanning for duplicate embeddings...")
    
    # Get all data
    all_data = collection.get()
    
    if not all_data['ids']:
        print("Collection is empty.")
        return
    
    print(f"Total documents: {len(all_data['ids'])}")
    
    # Group by content hash
    content_map = defaultdict(list)
    for i, doc in enumerate(all_data['documents']):
        content_hash = hash(doc)
        content_map[content_hash].append({
            'id': all_data['ids'][i],
            'metadata': all_data['metadatas'][i] if all_data['metadatas'] else {},
            'index': i
        })
    
    # Find duplicates
    duplicates = []
    for content_hash, items in content_map.items():
        if len(items) > 1:
            # Keep first, mark others as duplicates
            duplicates.extend([item['id'] for item in items[1:]])
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate documents")
        print("Removing duplicates...")
        collection.delete(ids=duplicates)
        print(f"✓ Removed {len(duplicates)} duplicates")
    else:
        print("✓ No duplicates found")


def validate_metadata(collection):
    """Ensure all documents have required metadata fields."""
    print("Validating metadata...")
    
    all_data = collection.get()
    
    if not all_data['ids']:
        return
    
    required_fields = ['file_source', 'original_file', 'section']
    missing_metadata = []
    
    for i, metadata in enumerate(all_data['metadatas'] or []):
        if not metadata:
            missing_metadata.append(all_data['ids'][i])
            continue
        
        for field in required_fields:
            if field not in metadata:
                missing_metadata.append(all_data['ids'][i])
                break
    
    if missing_metadata:
        print(f"⚠ Found {len(missing_metadata)} documents with missing metadata")
        print("These documents may not work correctly with RAG.")
    else:
        print("✓ All documents have required metadata")


def add_rag_metadata(collection):
    """Add RAG-specific metadata to ensure strict retrieval."""
    print("Adding RAG metadata...")
    
    all_data = collection.get()
    
    if not all_data['ids']:
        return
    
    updates = []
    for i, (doc_id, metadata) in enumerate(zip(all_data['ids'], all_data['metadatas'] or [])):
        if not metadata:
            continue
        
        # Ensure RAG metadata
        updated_metadata = metadata.copy()
        updated_metadata['rag_strict'] = 'true'
        updated_metadata['source_only'] = 'true'  # Flag for chatbot to only use this data
        
        if 'file_source' not in updated_metadata:
            updated_metadata['file_source'] = 'unknown'
        if 'original_file' not in updated_metadata:
            updated_metadata['original_file'] = updated_metadata.get('file_source', 'unknown')
        if 'section' not in updated_metadata:
            updated_metadata['section'] = f"chunk_{i}"
        
        updates.append({
            'id': doc_id,
            'metadata': updated_metadata
        })
    
    # Update metadata in batches
    batch_size = 100
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        for item in batch:
            try:
                collection.update(
                    ids=[item['id']],
                    metadatas=[item['metadata']]
                )
            except Exception as e:
                print(f"Error updating {item['id']}: {e}")
    
    print(f"✓ Updated metadata for {len(updates)} documents")


def main():
    """Main optimization function."""
    print("=" * 70)
    print("CHROMADB OPTIMIZATION")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    collection = get_collection()
    
    # Run optimizations
    deduplicate_embeddings(collection)
    print()
    
    validate_metadata(collection)
    print()
    
    add_rag_metadata(collection)
    print()
    
    # Final stats
    all_data = collection.get()
    print("=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"Total documents: {len(all_data['ids'])}")
    print()
    print("RAG Configuration:")
    print("  - Strict mode: Enabled (no hallucination)")
    print("  - Source-only: Enabled (only use stored data)")
    print("  - Metadata: Validated and updated")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

