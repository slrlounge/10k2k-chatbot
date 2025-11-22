#!/usr/bin/env python3
"""
Debug search - test what ChromaDB actually returns for a query.
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("DEBUG SEARCH - Testing W.A.V.E. Retrieval")
    print("=" * 70)
    print()
    
    # Initialize embeddings and vectorstore
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("✗ ERROR: OPENAI_API_KEY not set")
            return 1
        
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        
        print(f"✓ Connected to ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
        print(f"✓ Collection: {COLLECTION_NAME}")
        
        # Get total document count
        collection = client.get_collection(COLLECTION_NAME)
        total_docs = collection.count()
        print(f"✓ Total documents in collection: {total_docs}")
        print()
        
    except Exception as e:
        print(f"✗ Error connecting to ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test different query variations
    test_queries = [
        "W.A.V.E.",
        "WAVE",
        "wave",
        "wall art vision exercise",
        "What does W.A.V.E. stand for?",
        "W.A.V.E. acronym",
    ]
    
    for query in test_queries:
        print("=" * 70)
        print(f"Query: '{query}'")
        print("=" * 70)
        
        try:
            # Search with same parameters as serve.py
            docs_with_scores = vectorstore.similarity_search_with_score(
                query,
                k=10
            )
            
            if not docs_with_scores:
                print("  ✗ No results found")
                print()
                continue
            
            print(f"  Found {len(docs_with_scores)} results:")
            print()
            
            # Show top 5 results
            for i, (doc, score) in enumerate(docs_with_scores[:5], 1):
                metadata = doc.metadata if hasattr(doc, 'metadata') and doc.metadata else {}
                content_preview = doc.page_content[:200].replace('\n', ' ')
                
                filename = metadata.get('file_source') or metadata.get('original_file') or metadata.get('filename', 'unknown')
                
                print(f"  [{i}] Score: {score:.3f} (lower = better)")
                print(f"      File: {filename}")
                print(f"      Preview: {content_preview}...")
                
                # Check if WAVE/W.A.V.E. appears in content
                content_lower = doc.page_content.lower()
                if 'wave' in content_lower or 'w.a.v.e' in content_lower or 'wall art vision' in content_lower:
                    print(f"      ✓ Contains WAVE-related content!")
                print()
            
            # Check if any results pass the 2.0 threshold
            passing_results = [(doc, score) for doc, score in docs_with_scores if score < 2.0]
            print(f"  Results passing threshold (< 2.0): {len(passing_results)}/{len(docs_with_scores)}")
            print()
            
        except Exception as e:
            print(f"  ✗ Error searching: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Also search ChromaDB directly for text containing "WAVE"
    print("=" * 70)
    print("Direct ChromaDB Text Search")
    print("=" * 70)
    try:
        # Get all documents and search for WAVE in content
        all_docs = collection.get(limit=min(1000, total_docs))
        
        wave_docs = []
        for i, (doc_id, metadata, content) in enumerate(zip(
            all_docs.get('ids', []),
            all_docs.get('metadatas', []),
            all_docs.get('documents', [])
        )):
            content_lower = content.lower() if content else ""
            if 'wave' in content_lower or 'w.a.v.e' in content_lower or 'wall art vision' in content_lower:
                filename = (metadata.get('file_source') if metadata else None) or \
                          (metadata.get('original_file') if metadata else None) or \
                          'unknown'
                wave_docs.append((filename, content[:300]))
        
        if wave_docs:
            print(f"✓ Found {len(wave_docs)} documents containing 'WAVE' in content:")
            for filename, preview in wave_docs[:5]:
                print(f"  • {filename}")
                print(f"    {preview[:200]}...")
                print()
        else:
            print("✗ No documents found containing 'WAVE' in content")
            print("  This suggests the content may not be ingested, or uses different terminology")
        
    except Exception as e:
        print(f"✗ Error in direct search: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    exit(main())

