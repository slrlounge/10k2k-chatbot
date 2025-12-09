#!/usr/bin/env python3
"""
Create ChromaDB collection if it doesn't exist, then reset queue.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import json

# Import ChromaDB utilities with retry logic
try:
    from ingestion.utils_chromadb import (
        get_chroma_client_with_retry,
        get_collection_with_retry,
        get_collection_count_with_retry
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_chromadb import (
        get_chroma_client_with_retry,
        get_collection_with_retry,
        get_collection_count_with_retry
    )

load_dotenv()

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("CREATE COLLECTION AND RESET QUEUE")
    print("=" * 70)
    print()
    
    # Step 1: Create collection if it doesn't exist
    print("Step 1: Creating ChromaDB collection...")
    try:
        client = get_chroma_client_with_retry(host=CHROMA_HOST, port=CHROMA_PORT)
        print(f"  ✓ Connected to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        
        try:
            collection = get_collection_with_retry(client, COLLECTION_NAME)
            count = get_collection_count_with_retry(collection)
            print(f"  ✓ Collection '{COLLECTION_NAME}' already exists ({count:,} documents)")
        except Exception:
            # Collection doesn't exist, create it
            collection = get_collection_with_retry(client, COLLECTION_NAME)
            count = get_collection_count_with_retry(collection)
            print(f"  ✓ Collection '{COLLECTION_NAME}' created ({count:,} documents)")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    
    # Step 2: Find all .txt files
    print("Step 2: Scanning for .txt files...")
    txt_files = sorted(TRANSCRIPTS_DIR.rglob("*.txt"))
    print(f"  Found {len(txt_files)} .txt files")
    
    if len(txt_files) == 0:
        print("  ✗ No files found!")
        return 1
    
    # Step 3: Create fresh queue
    print("\nStep 3: Creating fresh queue...")
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    queue = {
        "pending": [str(f) for f in txt_files],
        "processing": [],
        "completed": [],
        "failed": []
    }
    
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)
    print(f"  ✓ Queue saved: {QUEUE_FILE}")
    print(f"  ✓ Pending: {len(queue['pending'])}")
    
    # Step 4: Reset checkpoint
    print("\nStep 4: Resetting checkpoint...")
    checkpoint = {
        "processed_files": {},
        "failed_files": {}
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"  ✓ Checkpoint reset: {CHECKPOINT_FILE}")
    
    print()
    print("=" * 70)
    print("✓ READY TO INGEST")
    print("=" * 70)
    print()
    print("✓ Using remote ChromaDB HttpClient only - no local storage")
    print("✓ Duplicate detection enabled - skipping existing chunks")
    print("✓ Retry logic enabled - handling network latency")
    print()
    print("Next step: Run ingestion worker:")
    print("  MAX_ITERATIONS=1000 python3 ingestion/process_queue_worker.py")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())


