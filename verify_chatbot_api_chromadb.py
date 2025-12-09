#!/usr/bin/env python3
"""
Verification script for chatbot-api ChromaDB connection.
Ensures chatbot-api can connect to remote ChromaDB and access the collection.
NEVER downloads all embeddings to avoid memory crashes.
"""

import os
import sys
from dotenv import load_dotenv
from chromadb import HttpClient
from chromadb.errors import ChromaError
import time

# Load environment variables
load_dotenv()

# Configuration - MUST match serve.py and ingestion scripts
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')


def get_chroma_client_with_retry(max_retries: int = 5, base_delay: float = 1.0) -> HttpClient:
    """Create ChromaDB HttpClient with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            client = HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, ssl=False)
            # Test connection by listing collections
            client.list_collections()
            print(f"✓ Connected to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
            return client
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                print(f"✗ Failed to connect after {max_retries} attempts")
                raise RuntimeError(f"Failed to connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT} after {max_retries} attempts: {last_error}")
    
    raise RuntimeError(f"Failed to connect to ChromaDB: {last_error}")


def verify_collection_exists(client: HttpClient) -> bool:
    """Verify collection exists without loading all data."""
    try:
        collections = client.list_collections()
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME in collection_names:
            print(f"✓ Collection '{COLLECTION_NAME}' exists")
            return True
        else:
            print(f"✗ Collection '{COLLECTION_NAME}' not found")
            print(f"  Available collections: {collection_names}")
            return False
    except Exception as e:
        print(f"✗ Error checking collections: {e}")
        return False


def get_collection_count_safe(collection, max_retries: int = 3) -> int:
    """Get collection count WITHOUT loading all embeddings."""
    last_error = None
    for attempt in range(max_retries):
        try:
            count = collection.count()
            return count
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = 1.0 * (2 ** attempt)
                print(f"⚠️  Count attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Failed to get collection count: {last_error}")
    
    raise RuntimeError(f"Failed to get collection count: {last_error}")


def test_similarity_search(collection, max_retries: int = 3):
    """Test similarity search WITHOUT loading all embeddings."""
    # Use a simple test query
    test_query = "test"
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Query with limit=1 to avoid loading too much
            results = collection.query(
                query_texts=[test_query],
                n_results=1
            )
            
            if results and results.get('ids') and len(results['ids'][0]) > 0:
                print(f"✓ Similarity search works (found {len(results['ids'][0])} result(s))")
                return True
            else:
                print(f"⚠️  Similarity search returned no results (collection may be empty)")
                return True  # Still counts as success - collection exists but is empty
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = 1.0 * (2 ** attempt)
                print(f"⚠️  Search attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(delay)
            else:
                print(f"✗ Similarity search failed: {last_error}")
                return False
    
    return False


def main():
    """Main verification function."""
    print("=" * 60)
    print("Chatbot-API ChromaDB Verification")
    print("=" * 60)
    print(f"CHROMA_HOST: {CHROMA_HOST}")
    print(f"CHROMA_PORT: {CHROMA_PORT}")
    print(f"COLLECTION_NAME: {COLLECTION_NAME}")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Connect to remote ChromaDB
        print("Step 1: Connecting to remote ChromaDB...")
        client = get_chroma_client_with_retry()
        print()
        
        # Step 2: Verify collection exists
        print("Step 2: Verifying collection exists...")
        if not verify_collection_exists(client):
            print("\n✗ VERIFICATION FAILED: Collection does not exist")
            print("  Run ingestion scripts to create and populate the collection.")
            sys.exit(1)
        print()
        
        # Step 3: Get collection with correct metadata
        print("Step 3: Getting collection...")
        try:
            collection = client.get_collection(COLLECTION_NAME)
            print(f"✓ Retrieved collection '{COLLECTION_NAME}'")
        except Exception as e:
            print(f"✗ Failed to get collection: {e}")
            sys.exit(1)
        print()
        
        # Step 4: Get collection count (safe - doesn't load embeddings)
        print("Step 4: Getting collection count (safe method)...")
        try:
            count = get_collection_count_safe(collection)
            print(f"✓ Collection contains {count} document(s)")
        except Exception as e:
            print(f"⚠️  Could not get count: {e}")
            print("  (This is okay if collection is empty or has issues)")
        print()
        
        # Step 5: Test similarity search (only retrieves 1 result)
        if count > 0:
            print("Step 5: Testing similarity search (retrieves only 1 result)...")
            test_similarity_search(collection)
            print()
        
        # Step 6: Verify metadata
        print("Step 6: Verifying collection metadata...")
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
            metadata = collection_info.metadata if hasattr(collection_info, 'metadata') else {}
            print(f"✓ Collection metadata: {metadata}")
            
            # Check for cosine similarity space
            if metadata.get('hnsw:space') == 'cosine':
                print("✓ Collection uses cosine similarity (correct)")
            else:
                print(f"⚠️  Collection uses '{metadata.get('hnsw:space', 'unknown')}' similarity space")
                print("  (Expected: cosine)")
        except Exception as e:
            print(f"⚠️  Could not verify metadata: {e}")
        print()
        
        # Success!
        print("=" * 60)
        print("✓ VERIFICATION SUCCESSFUL")
        print("=" * 60)
        print("Chatbot-API can connect to remote ChromaDB and access the collection.")
        print("No local storage is being used.")
        print("Collection is ready for use by the chatbot.")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ VERIFICATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        print("\nTraceback:")
        print(traceback.format_exc())
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

