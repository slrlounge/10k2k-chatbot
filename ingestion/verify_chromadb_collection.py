#!/usr/bin/env python3
"""
Verify ChromaDB Collection Exists
Check if the collection exists and has documents.
"""

import os
from dotenv import load_dotenv

# Import ChromaDB utilities with retry logic
try:
    from ingestion.utils_chromadb import (
        get_chroma_client_with_retry,
        get_collection_with_retry,
        get_collection_count_with_retry
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_chromadb import (
        get_chroma_client_with_retry,
        get_collection_with_retry,
        get_collection_count_with_retry
    )

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("CHROMADB COLLECTION VERIFICATION")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    try:
        client = get_chroma_client_with_retry(host=CHROMA_HOST, port=CHROMA_PORT)
        print(f"✓ Connected to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        
        # List all collections
        print("\n📋 Available Collections:")
        print("-" * 70)
        collections = client.list_collections()
        if collections:
            for col in collections:
                count = get_collection_count_with_retry(col)
                print(f"  • {col.name}: {count:,} documents")
        else:
            print("  (No collections found)")
        print()
        
        # Check if our collection exists
        print(f"🔍 Checking collection '{COLLECTION_NAME}':")
        print("-" * 70)
        try:
            collection = get_collection_with_retry(client, COLLECTION_NAME)
            count = get_collection_count_with_retry(collection)
            print(f"  ✓ Collection exists")
            print(f"  ✓ Documents: {count:,}")
            
            if count > 0:
                # Get a sample document
                sample = collection.get(limit=1)
                if sample['ids']:
                    print(f"\n  Sample document ID: {sample['ids'][0]}")
                    if sample['metadatas']:
                        print(f"  Sample metadata: {sample['metadatas'][0]}")
        except Exception as e:
            print(f"  ✗ Collection does not exist: {e}")
            print()
            print("  💡 Solution: Run ingestion to create the collection:")
            print("     python3 ingestion/generate_file_queue.py")
            print("     python3 ingestion/ingest_one_file.py")
        
    except Exception as e:
        print(f"✗ Error connecting to ChromaDB: {e}")
        return 1
    
    print()
    print("=" * 70)
    return 0

if __name__ == "__main__":
    exit(main())

