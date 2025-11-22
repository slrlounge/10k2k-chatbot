#!/usr/bin/env python3
"""
Diagnose why collection appears empty after ingestion.
"""

import os
from dotenv import load_dotenv
import chromadb

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("DIAGNOSING EMPTY COLLECTION ISSUE")
    print("=" * 70)
    print()
    
    # Step 1: Connect to ChromaDB
    print("Step 1: Connecting to ChromaDB...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        print(f"  ✓ Connected to {CHROMA_HOST}:{CHROMA_PORT}")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return 1
    
    # Step 2: List all collections
    print("\nStep 2: Listing all collections...")
    try:
        collections = client.list_collections()
        print(f"  Found {len(collections)} collection(s):")
        for col in collections:
            print(f"    - {col.name}")
            try:
                count = col.count()
                print(f"      Document count: {count:,}")
            except Exception as e:
                print(f"      Error getting count: {e}")
    except Exception as e:
        print(f"  ✗ Error listing collections: {e}")
        return 1
    
    # Step 3: Check target collection
    print(f"\nStep 3: Checking target collection '{COLLECTION_NAME}'...")
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"  ✓ Collection exists")
        print(f"  ✓ Document count: {count:,}")
        
        if count == 0:
            print()
            print("  ⚠️  Collection is empty!")
            print()
            print("  Possible causes:")
            print("    1. Ingestion didn't complete successfully")
            print("    2. Ingestion wrote to a different collection")
            print("    3. Data was written but then deleted")
            print("    4. Connection issue during ingestion")
            print()
            print("  Next steps:")
            print("    1. Check ingestion logs in ingest-chromadb service")
            print("    2. Verify ingestion completed successfully")
            print("    3. Check if data exists in other collections")
            print("    4. Re-run ingestion if needed")
        else:
            # Get sample documents
            print()
            print("  Sample documents:")
            sample = collection.get(limit=3)
            for i, (doc_id, metadata, content) in enumerate(zip(
                sample.get('ids', []),
                sample.get('metadatas', []),
                sample.get('documents', [])
            ), 1):
                filename = metadata.get('file_source') if metadata else 'unknown'
                print(f"    [{i}] {filename}")
                print(f"        Preview: {content[:100] if content else 'N/A'}...")
        
    except chromadb.errors.NotFoundError:
        print(f"  ✗ Collection '{COLLECTION_NAME}' does not exist")
        print()
        print("  This means:")
        print("    - Ingestion never created the collection")
        print("    - Or collection was deleted")
        print()
        print("  Solution: Run ingestion again")
        return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 4: Check persistent disk usage
    print("\nStep 4: Checking persistent disk...")
    print("  (Run this in chromadb service Shell to check disk usage)")
    print("  Command: df -h /chroma/chroma")
    print("  Command: ls -lah /chroma/chroma")
    
    print()
    print("=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    exit(main())

