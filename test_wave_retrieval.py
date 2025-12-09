#!/usr/bin/env python3
"""
Test if WAVE-related documents are in ChromaDB and can be retrieved.
"""

import os
from dotenv import load_dotenv
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
CHROMA_URL = os.getenv('CHROMA_URL', None)
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("TESTING WAVE RETRIEVAL FROM CHROMADB")
    print("=" * 70)
    
    try:
        # Connect to ChromaDB
        if CHROMA_URL:
            url = CHROMA_URL.replace('http://', '').replace('https://', '')
            if ':' in url:
                host, port = url.split(':')
                port = int(port)
            else:
                host = url
                port = 8000
            print(f"Connecting to: {host}:{port}")
            client = chromadb.HttpClient(host=host, port=port)
        else:
            print(f"Connecting to: {CHROMA_HOST}:{CHROMA_PORT}")
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        collection = client.get_collection(COLLECTION_NAME)
        total_count = collection.count()
        print(f"\n📊 Total documents in ChromaDB: {total_count}")
        
        if total_count == 0:
            print("\n⚠️  No documents found in ChromaDB!")
            print("   The WAVE documents need to be ingested.")
            return 1
        
        # Initialize vectorstore for similarity search
        print("\n🔍 Testing similarity search for WAVE...")
        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'))
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        
        # Test queries
        test_queries = [
            "What does W.A.V.E. stand for?",
            "WAVE",
            "wall art vision exercise",
            "W.A.V.E. framework"
        ]
        
        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"Query: '{query}'")
            print('='*70)
            
            docs_with_scores = vectorstore.similarity_search_with_score(query, k=5)
            
            if not docs_with_scores:
                print("  ✗ No documents found!")
                continue
            
            print(f"  Found {len(docs_with_scores)} documents:")
            
            for i, (doc, score) in enumerate(docs_with_scores, 1):
                print(f"\n  [{i}] Score: {score:.4f} (lower = better)")
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                filename = (
                    metadata.get('filename') or
                    metadata.get('file_source') or
                    metadata.get('original_file') or
                    'Unknown'
                )
                print(f"      File: {filename}")
                
                # Check if content mentions WAVE
                content_lower = doc.page_content.lower()
                if 'wave' in content_lower or 'w.a.v.e' in content_lower or 'wall art vision' in content_lower:
                    print(f"      ✓ Contains WAVE-related content")
                    # Show snippet
                    snippet = doc.page_content[:300].replace('\n', ' ')
                    print(f"      Preview: {snippet}...")
                else:
                    print(f"      ⚠️  Doesn't appear to contain WAVE content")
                    snippet = doc.page_content[:200].replace('\n', ' ')
                    print(f"      Preview: {snippet}...")
        
        # Also search directly in ChromaDB for WAVE mentions
        print(f"\n{'='*70}")
        print("SEARCHING CHROMADB DIRECTLY FOR 'WAVE' IN CONTENT")
        print('='*70)
        
        # Get sample of documents and search for WAVE
        sample_size = min(1000, total_count)
        all_docs = collection.get(limit=sample_size)
        
        wave_docs = []
        for i, (doc_id, content, metadata) in enumerate(zip(
            all_docs.get('ids', []),
            all_docs.get('documents', []),
            all_docs.get('metadatas', [])
        )):
            if content and ('wave' in content.lower() or 'w.a.v.e' in content.lower() or 'wall art vision' in content.lower()):
                filename = (
                    (metadata or {}).get('filename') or
                    (metadata or {}).get('file_source') or
                    (metadata or {}).get('original_file') or
                    doc_id
                )
                wave_docs.append((filename, content[:200]))
        
        print(f"\nFound {len(wave_docs)} documents containing 'WAVE' in first {sample_size} documents:")
        for filename, preview in wave_docs[:10]:  # Show first 10
            print(f"  ✓ {filename}")
            print(f"    {preview}...")
        
        if len(wave_docs) == 0:
            print("\n⚠️  No WAVE documents found in ChromaDB!")
            print("   This suggests the WAVE files haven't been ingested yet.")
            print("   Files that should contain WAVE:")
            print("   - 10K2Kv2/14_STEP FOURTEEN/14 - SALES HOW TO CLOSE EVERY CLIENT v2_1.txt")
            print("   - 10K2Kv2/14_STEP FOURTEEN/s14-02-the-wave-exercise_01.txt")
            print("   - And many others in STEP FOURTEEN")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

