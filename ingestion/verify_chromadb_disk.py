#!/usr/bin/env python3
"""
Verify ChromaDB is using persistent disk and check collection status.
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
    print("CHROMADB PERSISTENT DISK VERIFICATION")
    print("=" * 70)
    print()
    
    # Check connection
    print("Step 1: Connecting to ChromaDB...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        print(f"  ✓ Connected to {CHROMA_HOST}:{CHROMA_PORT}")
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        return 1
    
    print()
    
    # Check if collection exists
    print("Step 2: Checking collection...")
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"  ✓ Collection '{COLLECTION_NAME}' exists")
        print(f"  ✓ Document count: {count}")
        
        if count == 0:
            print()
            print("  ⚠️  WARNING: Collection is empty!")
            print("     This could mean:")
            print("     1. Data was never ingested")
            print("     2. Data was ingested before persistent disk was added")
            print("     3. ChromaDB needs to be redeployed to mount the disk")
            print()
            print("     Next steps:")
            print("     1. Redeploy ChromaDB service (to mount persistent disk)")
            print("     2. Re-ingest data from ingest-chromadb service")
        else:
            print(f"  ✓ Data is present ({count} documents)")
            
    except chromadb.errors.NotFoundError:
        print(f"  ✗ Collection '{COLLECTION_NAME}' does not exist")
        print()
        print("  Next steps:")
        print("     1. Redeploy ChromaDB service (to mount persistent disk)")
        print("     2. Run: python3 ingestion/create_collection_and_reset.py")
        print("     3. Run: MAX_ITERATIONS=1000 python3 ingestion/process_queue_worker.py")
        return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    exit(main())

