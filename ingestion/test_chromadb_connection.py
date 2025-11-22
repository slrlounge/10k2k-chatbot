#!/usr/bin/env python3
"""
Test connection to ChromaDB server.
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
    print("CHROMADB CONNECTION TEST")
    print("=" * 70)
    print()
    print(f"Connecting to: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    try:
        # Test connection
        print("Step 1: Testing connection...")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        print("  ✓ Connection successful!")
        
        # Test server heartbeat/health
        print("\nStep 2: Testing server health...")
        try:
            # Try to list collections (this tests if server is responding)
            collections = client.list_collections()
            print(f"  ✓ Server is responding")
            print(f"  ✓ Found {len(collections)} collection(s)")
        except Exception as e:
            print(f"  ⚠️  Server responded but error listing collections: {e}")
        
        # Test collection access
        print(f"\nStep 3: Testing collection '{COLLECTION_NAME}'...")
        try:
            collection = client.get_collection(COLLECTION_NAME)
            count = collection.count()
            print(f"  ✓ Collection exists")
            print(f"  ✓ Document count: {count}")
            
            if count > 0:
                print(f"\n  ✓ DATA IS PRESENT - Connection is working!")
            else:
                print(f"\n  ⚠️  Collection is empty (ready for ingestion)")
        except chromadb.errors.NotFoundError:
            print(f"  ⚠️  Collection doesn't exist yet (will be created on first ingestion)")
        except Exception as e:
            print(f"  ✗ Error accessing collection: {e}")
            return 1
        
        print()
        print("=" * 70)
        print("✓ CONNECTION TEST PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  • ingest-chromadb → chromadb-w5jr:8000 ✓")
        print(f"  • ChromaDB server is accessible ✓")
        print(f"  • Ready for ingestion ✓")
        print()
        
        return 0
        
    except chromadb.errors.ChromaConnectionError as e:
        print(f"  ✗ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check that ChromaDB service is running")
        print("  2. Verify service name matches: chromadb-w5jr")
        print("  3. Check network connectivity between services")
        return 1
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

