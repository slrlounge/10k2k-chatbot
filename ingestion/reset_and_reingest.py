#!/usr/bin/env python3
"""
Reset queue and re-ingest all files.
Use this when checkpoint says files are processed but ChromaDB is empty.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import chromadb

load_dotenv()

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("RESET QUEUE AND RE-INGEST")
    print("=" * 70)
    print()
    
    # Check ChromaDB
    print("Step 1: Checking ChromaDB...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"  Current documents in ChromaDB: {count}")
    except Exception as e:
        print(f"  Error checking ChromaDB: {e}")
        return 1
    
    # Find all .txt files
    print("\nStep 2: Scanning for transcript files...")
    txt_files = list(TRANSCRIPTS_DIR.rglob("*.txt"))
    print(f"  Found {len(txt_files)} .txt files")
    
    if len(txt_files) == 0:
        print("  ✗ No files found!")
        return 1
    
    # Create fresh queue
    print("\nStep 3: Creating fresh queue...")
    queue = {
        "pending": [str(f) for f in sorted(txt_files)],
        "processing": [],
        "completed": [],
        "failed": []
    }
    
    # Ensure checkpoint directory exists
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Save queue
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)
    print(f"  ✓ Queue saved: {QUEUE_FILE}")
    print(f"  ✓ Pending: {len(queue['pending'])}")
    print(f"  ✓ Completed: {len(queue['completed'])}")
    
    # Reset checkpoint
    print("\nStep 4: Resetting checkpoint...")
    checkpoint = {
        "processed_files": {},
        "failed_files": {}
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"  ✓ Checkpoint reset: {CHECKPOINT_FILE}")
    
    print("\n" + "=" * 70)
    print("✓ QUEUE RESET COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run: MAX_ITERATIONS=1000 python3 ingestion/process_queue_worker.py")
    print("  2. Monitor: python3 ingestion/check_ingestion_status.py")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())

