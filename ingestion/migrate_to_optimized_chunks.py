#!/usr/bin/env python3
"""
Migrate Existing Files to Optimized Chunking
Removes old embeddings and re-ingests with new optimized settings (1000 tokens, 200 overlap).
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import chromadb

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))


def get_collection():
    """Get ChromaDB collection."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error getting collection: {e}")
        sys.exit(1)


def get_files_to_migrate(collection):
    """Get list of files that need migration (based on old chunking)."""
    print("Scanning ChromaDB for files to migrate...")
    
    all_data = collection.get()
    
    if not all_data['ids']:
        print("No documents in ChromaDB.")
        return []
    
    # Group by file_source
    file_sources = {}
    for i, metadata in enumerate(all_data['metadatas'] or []):
        if not metadata:
            continue
        
        file_source = metadata.get('file_source', 'unknown')
        if file_source not in file_sources:
            file_sources[file_source] = {
                'ids': [],
                'chunk_count': 0,
                'max_chunk_index': 0
            }
        
        file_sources[file_source]['ids'].append(all_data['ids'][i])
        file_sources[file_source]['chunk_count'] += 1
        
        chunk_idx = metadata.get('chunk_index', 0)
        if chunk_idx > file_sources[file_source]['max_chunk_index']:
            file_sources[file_source]['max_chunk_index'] = chunk_idx
    
    # Identify files that likely used old chunking (many small chunks)
    files_to_migrate = []
    for file_source, info in file_sources.items():
        # If file has many chunks relative to size, likely old chunking
        # Or if chunk_index suggests old 500-token chunks
        if info['chunk_count'] > 3:  # More than 3 chunks suggests old chunking
            file_path = TRANSCRIPTS_DIR / file_source
            if file_path.exists():
                files_to_migrate.append(str(file_path))
    
    return files_to_migrate


def remove_file_from_chromadb(collection, file_source: str):
    """Remove all chunks for a specific file from ChromaDB."""
    print(f"Removing old embeddings for: {file_source}")
    
    all_data = collection.get()
    
    if not all_data['ids']:
        return 0
    
    ids_to_delete = []
    for i, metadata in enumerate(all_data['metadatas'] or []):
        if metadata and metadata.get('file_source') == file_source:
            ids_to_delete.append(all_data['ids'][i])
    
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"  Removed {len(ids_to_delete)} old chunks")
        return len(ids_to_delete)
    
    return 0


def update_checkpoint(file_path: Path, remove: bool = True):
    """Update checkpoint to mark file for re-ingestion."""
    checkpoint = {}
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
        except Exception:
            pass
    
    file_str = str(file_path)
    
    if remove:
        # Remove from processed_files so it gets re-ingested
        if 'processed_files' in checkpoint:
            checkpoint['processed_files'].pop(file_str, None)
        if 'failed_files' in checkpoint:
            checkpoint['failed_files'].pop(file_str, None)
    else:
        # Mark as needing migration
        if 'needs_migration' not in checkpoint:
            checkpoint['needs_migration'] = []
        if file_str not in checkpoint['needs_migration']:
            checkpoint['needs_migration'].append(file_str)
    
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def main():
    """Main migration function."""
    print("=" * 70)
    print("MIGRATE TO OPTIMIZED CHUNKING")
    print("=" * 70)
    print("This will remove old embeddings and mark files for re-ingestion")
    print("with optimized settings (1000 tokens, 200 overlap).")
    print()
    
    collection = get_collection()
    
    # Get files to migrate
    files_to_migrate = get_files_to_migrate(collection)
    
    if not files_to_migrate:
        print("No files need migration (or collection is empty).")
        return 0
    
    print(f"\nFound {len(files_to_migrate)} files to migrate:")
    for f in files_to_migrate[:10]:
        print(f"  • {Path(f).name}")
    if len(files_to_migrate) > 10:
        print(f"  ... and {len(files_to_migrate) - 10} more")
    
    print("\n" + "=" * 70)
    response = input("Remove old embeddings and mark for re-ingestion? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return 0
    
    # Remove old embeddings and update checkpoint
    removed_count = 0
    for file_path_str in files_to_migrate:
        file_path = Path(file_path_str)
        relative_path = file_path.relative_to(TRANSCRIPTS_DIR)
        
        # Remove from ChromaDB
        removed = remove_file_from_chromadb(collection, str(relative_path))
        removed_count += removed
        
        # Update checkpoint
        update_checkpoint(file_path, remove=True)
    
    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"Removed embeddings for {len(files_to_migrate)} files")
    print(f"Total chunks removed: {removed_count}")
    print()
    print("Next steps:")
    print("1. Regenerate queue: python3 ingestion/generate_file_queue.py")
    print("2. Re-ingest files: python3 ingestion/process_queue_worker.py")
    print()
    print("Files will be re-ingested with optimized settings:")
    print("  - Chunk size: 1000 tokens")
    print("  - Overlap: 200 tokens (20%)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

