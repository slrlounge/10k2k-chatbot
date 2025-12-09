#!/usr/bin/env python3
"""
Check actual document count in ChromaDB
This shows the REAL number of documents, regardless of checkpoint status.
"""

import os
import sys
from dotenv import load_dotenv
import chromadb

load_dotenv()

# Get ChromaDB connection info
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

print("\n" + "="*70)
print("🔍 CHECKING ACTUAL CHROMADB DOCUMENT COUNT")
print("="*70)
print()
print(f"ChromaDB Host: {CHROMA_HOST}")
print(f"ChromaDB Port: {CHROMA_PORT}")
print(f"Collection: {COLLECTION_NAME}")
print()

try:
    # Connect to ChromaDB
    print("Connecting to ChromaDB...")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    # Test connection
    heartbeat = client.heartbeat()
    print(f"✅ Connected! Heartbeat: {heartbeat}")
    print()
    
    # Get collection
    print(f"Getting collection '{COLLECTION_NAME}'...")
    collection = client.get_collection(name=COLLECTION_NAME)
    
    # Get actual count
    count = collection.count()
    
    print()
    print("="*70)
    print("📊 ACTUAL DOCUMENT COUNT IN CHROMADB")
    print("="*70)
    print()
    print(f"Total documents stored: {count}")
    print()
    
    # Estimate files processed
    # Each file creates multiple chunks (documents)
    # Average: ~10-50 chunks per file depending on size
    # So if we have 1000 documents, that's roughly 20-100 files
    
    if count > 0:
        # Try to get unique filenames from metadata
        try:
            # Get a sample of documents to check metadata
            results = collection.get(limit=min(100, count))
            if results and results.get('metadatas'):
                filenames = set()
                for metadata in results['metadatas']:
                    if metadata and 'filename' in metadata:
                        filenames.add(metadata['filename'])
                
                print(f"Unique filenames in sample: {len(filenames)}")
                print(f"(Sample size: {min(100, count)} documents)")
                print()
                
                # Estimate total unique files
                if count > 100:
                    estimated_files = int((len(filenames) / min(100, count)) * count / 20)  # Rough estimate: 20 chunks per file
                    print(f"Estimated unique files processed: ~{estimated_files}")
                else:
                    print(f"Unique files in collection: {len(filenames)}")
        except Exception as e:
            print(f"Could not analyze metadata: {e}")
    
    print()
    print("="*70)
    print()
    
    # Compare to checkpoint
    print("📋 CHECKPOINT STATUS:")
    print(f"  Checkpoint shows: 12/159 files")
    print(f"  Actual documents: {count}")
    print()
    
    if count > 0:
        print("✅ ChromaDB HAS DATA!")
        print("   Even if checkpoint shows 12, ChromaDB may have more.")
        print("   This is normal if service restarted.")
    else:
        print("⚠️  ChromaDB is EMPTY")
        print("   Ingestion may not have completed successfully.")
    
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

