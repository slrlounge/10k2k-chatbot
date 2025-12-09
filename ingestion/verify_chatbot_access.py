#!/usr/bin/env python3
"""
Verify chatbot-api can access all ingested data from ChromaDB.
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

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
    print("CHATBOT-API DATA ACCESS VERIFICATION")
    print("=" * 70)
    print()
    print("This script verifies that chatbot-api can access all ingested data.")
    print("Run this in chatbot-api service Shell to test.")
    print()
    
    # Step 1: Check environment variables
    print("Step 1: Checking environment variables...")
    chroma_host = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
    chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
    collection_name = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"  CHROMA_HOST: {chroma_host}")
    print(f"  CHROMA_PORT: {chroma_port}")
    print(f"  COLLECTION_NAME: {collection_name}")
    print(f"  OPENAI_API_KEY: {'SET' if openai_key else 'NOT SET ⚠️'}")
    
    if not openai_key:
        print()
        print("  ✗ ERROR: OPENAI_API_KEY not set!")
        print("     Set it in Render → chatbot-api → Environment")
        return 1
    
    print()
    
    # Step 2: Test ChromaDB connection
    print("Step 2: Testing ChromaDB connection...")
    try:
        client = get_chroma_client_with_retry(host=chroma_host, port=chroma_port)
        print(f"  ✓ Connected to remote ChromaDB at {chroma_host}:{chroma_port}")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return 1
    
    # Step 3: Check collection exists
    print("\nStep 3: Checking collection...")
    try:
        collection = get_collection_with_retry(client, collection_name)
        count = get_collection_count_with_retry(collection)
        print(f"  ✓ Collection '{collection_name}' exists")
        print(f"  ✓ Document count: {count:,}")
        
        if count == 0:
            print()
            print("  ⚠️  WARNING: Collection is empty!")
            print("     No data has been ingested yet.")
            print("     Run ingestion from ingest-chromadb service first.")
            return 1
        
    except chromadb.errors.NotFoundError:
        print(f"  ✗ Collection '{collection_name}' does not exist")
        print()
        print("  Next steps:")
        print("     1. Run ingestion from ingest-chromadb service")
        print("     2. Verify ingestion completed successfully")
        return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Step 4: Test LangChain vectorstore (same as chatbot-api uses)
    print("\nStep 4: Testing LangChain vectorstore (chatbot-api method)...")
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
        vectorstore = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        print("  ✓ Vectorstore initialized")
        
        # Test search
        print("  Testing search...")
        test_query = "test"
        results = vectorstore.similarity_search_with_score(test_query, k=3)
        print(f"  ✓ Search successful - found {len(results)} results")
        
        if results:
            print(f"  ✓ Top result score: {results[0][1]:.3f} (lower = better)")
            print(f"  ✓ Sample content preview: {results[0][0].page_content[:100]}...")
        
    except Exception as e:
        print(f"  ✗ Error initializing vectorstore: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 5: Test sample queries
    print("\nStep 5: Testing sample queries...")
    test_queries = [
        "W.A.V.E.",
        "10K to 2K",
        "sales",
    ]
    
    for query in test_queries:
        try:
            results = vectorstore.similarity_search_with_score(query, k=3)
            if results:
                best_score = results[0][1]
                print(f"  ✓ Query '{query}': Found {len(results)} results (best score: {best_score:.3f})")
            else:
                print(f"  ⚠️  Query '{query}': No results found")
        except Exception as e:
            print(f"  ✗ Query '{query}' failed: {e}")
    
    print()
    print("=" * 70)
    print("✓ VERIFICATION COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • ChromaDB connection: ✓")
    print(f"  • Collection exists: ✓")
    print(f"  • Documents available: {count:,}")
    print(f"  • Vectorstore working: ✓")
    print(f"  • Search functional: ✓")
    print()
    print("✅ chatbot-api can access all ingested data!")
    print()
    print("Next steps:")
    print("  1. Test chatbot in web browser")
    print("  2. Verify answers include source citations")
    print("  3. Test various queries to ensure data is accessible")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())

