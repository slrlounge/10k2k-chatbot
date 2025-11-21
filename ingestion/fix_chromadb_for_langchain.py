#!/usr/bin/env python3
"""
Fix ChromaDB Collection for LangChain Compatibility
Ensures the collection exists and is accessible to LangChain's Chroma wrapper.
"""

import os
from dotenv import load_dotenv
import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("FIXING CHROMADB FOR LANGCHAIN COMPATIBILITY")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    # Step 1: Check if collection exists with direct client
    print("Step 1: Checking collection with direct ChromaDB client...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        collections = client.list_collections()
        print(f"  Found {len(collections)} collections:")
        for col in collections:
            print(f"    • {col.name}: {col.count()} documents")
        
        # Check if our collection exists
        try:
            collection = client.get_collection(COLLECTION_NAME)
            print(f"\n  ✓ Collection '{COLLECTION_NAME}' exists")
            print(f"  ✓ Documents: {collection.count()}")
        except Exception as e:
            print(f"\n  ✗ Collection '{COLLECTION_NAME}' does not exist")
            print(f"  Error: {e}")
            print("\n  Creating collection...")
            collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"  ✓ Collection '{COLLECTION_NAME}' created")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    print()
    
    # Step 2: Test LangChain Chroma wrapper
    print("Step 2: Testing LangChain Chroma wrapper...")
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("  ✗ OPENAI_API_KEY not set")
            return 1
        
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        
        print(f"  ✓ LangChain Chroma wrapper initialized")
        print(f"  ✓ Collection accessible: {COLLECTION_NAME}")
        
        # Try a simple query to verify it works
        try:
            results = vectorstore.similarity_search("test", k=1)
            print(f"  ✓ Query test successful (found {len(results)} results)")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"  ⚠ Collection exists but query failed: {e}")
                print(f"  This might be because collection is empty.")
            else:
                print(f"  ✗ Query test failed: {e}")
                return 1
        
    except Exception as e:
        print(f"  ✗ LangChain Chroma wrapper failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("=" * 70)
    print("✓ CHROMADB IS CONFIGURED CORRECTLY FOR LANGCHAIN")
    print("=" * 70)
    print()
    print("If chatbot still shows errors:")
    print("  1. Restart the chatbot-api service")
    print("  2. Check that COLLECTION_NAME env var matches in both services")
    print("  3. Verify documents exist in the collection")
    
    return 0

if __name__ == "__main__":
    exit(main())

