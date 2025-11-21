#!/usr/bin/env python3
"""
Check what metadata fields are actually stored in ChromaDB documents.
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
    print("CHECKING METADATA IN CHROMADB")
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
        
        # Get a sample of documents
        print(f"\nFetching sample documents...")
        sample = collection.get(limit=10)
        
        if not sample.get('metadatas'):
            print("No documents found!")
            return
        
        print(f"\nFound {len(sample['metadatas'])} sample documents\n")
        print("=" * 70)
        print("METADATA STRUCTURE:")
        print("=" * 70)
        
        all_keys = set()
        for metadata in sample['metadatas']:
            if metadata:
                all_keys.update(metadata.keys())
        
        print(f"\nAll unique metadata keys found: {sorted(all_keys)}")
        
        for i, metadata in enumerate(sample['metadatas'][:5], 1):
            print(f"\n[Document {i}]")
            print(f"  All metadata keys: {list(metadata.keys()) if metadata else 'None'}")
            if metadata:
                for key, value in metadata.items():
                    print(f"  {key}: {repr(value)}")
            else:
                print("  ⚠️  Metadata is None or empty!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

