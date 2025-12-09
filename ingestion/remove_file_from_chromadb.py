#!/usr/bin/env python3
"""
Remove Specific File from ChromaDB
Useful for cleaning up before re-ingestion with optimized settings.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))


def remove_file_embeddings(file_path: str):
    """Remove all embeddings for a specific file."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error getting collection: {e}")
        return False
    
    # Convert to relative path
    if Path(file_path).is_absolute():
        relative_path = Path(file_path).relative_to(TRANSCRIPTS_DIR)
    else:
        relative_path = Path(file_path)
    
    file_source = str(relative_path)
    
    # Get all documents
    all_data = collection.get()
    
    if not all_data['ids']:
        print("Collection is empty.")
        return False
    
    # Find IDs to delete
    ids_to_delete = []
    for i, metadata in enumerate(all_data['metadatas'] or []):
        if metadata and metadata.get('file_source') == file_source:
            ids_to_delete.append(all_data['ids'][i])
    
    if not ids_to_delete:
        print(f"No embeddings found for: {file_source}")
        return False
    
    # Delete
    collection.delete(ids=ids_to_delete)
    print(f"✓ Removed {len(ids_to_delete)} chunks for: {file_source}")
    return True


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 remove_file_from_chromadb.py <file_path>")
        print("Example: python3 remove_file_from_chromadb.py '01_STEP ONE/00-S1-ALL-IN-ONE_01.txt'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = remove_file_embeddings(file_path)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

