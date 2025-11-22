#!/usr/bin/env python3
"""
Quick check: Are WAVE documents in ChromaDB?
"""

import os
from dotenv import load_dotenv
import chromadb

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
CHROMA_URL = os.getenv('CHROMA_URL', None)
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("QUICK WAVE CHECK")
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
        total = collection.count()
        print(f"\n✅ Connected to ChromaDB")
        print(f"📊 Total documents: {total}")
        
        if total == 0:
            print("\n❌ ChromaDB is EMPTY! No documents ingested.")
            print("\nTo fix, run ingestion:")
            print("  python3 ingestion/ingest_pre_split_files.py")
            return
        
        # Check for WAVE content directly
        print("\n🔍 Searching for WAVE content in documents...")
        print("   (Checking up to 10,000 documents)")
        
        sample_size = min(10000, total)
        sample = collection.get(limit=sample_size)
        
        wave_docs = []
        for doc_id, content, metadata in zip(
            sample.get('ids', []),
            sample.get('documents', []),
            sample.get('metadatas', [])
        ):
            if content:
                content_lower = content.lower()
                if ('wave' in content_lower and 'wall art vision' in content_lower) or 'w.a.v.e' in content_lower:
                    filename = (
                        (metadata or {}).get('filename') or
                        (metadata or {}).get('file_source') or
                        (metadata or {}).get('original_file') or
                        doc_id
                    )
                    # Find snippet with definition
                    if 'wall art vision exercise' in content_lower:
                        idx = content_lower.find('wall art vision exercise')
                        snippet = content[max(0, idx-30):idx+100]
                        wave_docs.append((filename, snippet))
                    else:
                        wave_docs.append((filename, content[:150]))
        
        print(f"\n📋 Found {len(wave_docs)} documents containing WAVE")
        
        if len(wave_docs) == 0:
            print("\n" + "=" * 70)
            print("❌ PROBLEM IDENTIFIED: NO WAVE DOCUMENTS IN CHROMADB!")
            print("=" * 70)
            print("\nThe WAVE files exist in your source directory but haven't been ingested.")
            print("\nTo fix this:")
            print("\n1. Ingest all files:")
            print("   python3 ingestion/ingest_pre_split_files.py")
            print("\n2. Or ingest specific WAVE files:")
            print("   python3 ingestion/ingest_single_transcript_ultra_minimal.py '10K2Kv2/14_STEP FOURTEEN/14 - SALES HOW TO CLOSE EVERY CLIENT v2_1.txt'")
            print("   python3 ingestion/ingest_single_transcript_ultra_minimal.py '10K2Kv2/14_STEP FOURTEEN/s14-02-the-wave-exercise_01.txt'")
            print("\n3. After ingestion, restart your server")
            return
        
        # Show some examples
        print("\n" + "=" * 70)
        print("✅ WAVE DOCUMENTS FOUND!")
        print("=" * 70)
        print(f"\nFound {len(wave_docs)} documents. Showing first 5:")
        for i, (filename, snippet) in enumerate(wave_docs[:5], 1):
            print(f"\n[{i}] {filename}")
            print(f"    ...{snippet}...")
        
        print("\n" + "=" * 70)
        print("DIAGNOSIS")
        print("=" * 70)
        print("\n✅ WAVE documents ARE in ChromaDB")
        print("❌ But chatbot still says 'no information'")
        print("\nPossible causes:")
        print("1. Server hasn't been restarted (code changes not applied)")
        print("2. Similarity search not finding them (check server logs)")
        print("3. Documents being filtered out by score threshold")
        print("\nNext steps:")
        print("1. Restart your server to apply code changes")
        print("2. Check server logs for retrieval scores")
        print("3. Try query: 'wall art vision exercise' (full phrase)")
        
    except chromadb.errors.NotFoundError:
        print(f"\n❌ Collection '{COLLECTION_NAME}' not found!")
        print("   Need to create collection and ingest documents first.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

