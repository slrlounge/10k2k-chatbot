#!/usr/bin/env python3
"""
Check Ingestion Status
Quick script to monitor ingestion progress.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import chromadb

load_dotenv()

QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')


def load_json_file(file_path: Path, default: dict) -> dict:
    """Load JSON file safely."""
    if not file_path.exists():
        return default
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception:
        return default


def get_chromadb_count():
    """Get document count from ChromaDB."""
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        return count
    except Exception as e:
        return f"Error: {e}"


def main():
    """Display ingestion status."""
    print("=" * 70)
    print("INGESTION STATUS")
    print("=" * 70)
    print()
    
    # Queue status
    queue = load_json_file(QUEUE_FILE, {"pending": [], "processing": [], "completed": [], "failed": []})
    
    print("📋 QUEUE STATUS")
    print("-" * 70)
    print(f"  Pending:    {len(queue.get('pending', [])):>5} files")
    print(f"  Processing: {len(queue.get('processing', [])):>5} files")
    print(f"  Completed:  {len(queue.get('completed', [])):>5} files")
    print(f"  Failed:     {len(queue.get('failed', [])):>5} files")
    
    total = len(queue.get('pending', [])) + len(queue.get('completed', [])) + len(queue.get('failed', []))
    if total > 0:
        progress = (len(queue.get('completed', [])) / total) * 100
        print(f"\n  Progress:   {progress:.1f}%")
    
    # Currently processing
    if queue.get('processing'):
        print(f"\n  ⏳ Currently processing:")
        for file_path in queue['processing'][:3]:  # Show first 3
            print(f"    • {Path(file_path).name}")
        if len(queue['processing']) > 3:
            print(f"    ... and {len(queue['processing']) - 3} more")
    
    print()
    
    # Checkpoint status
    checkpoint = load_json_file(CHECKPOINT_FILE, {"processed_files": {}, "failed_files": {}})
    
    print("📝 CHECKPOINT STATUS")
    print("-" * 70)
    print(f"  Processed:  {len(checkpoint.get('processed_files', {})):>5} files")
    print(f"  Failed:     {len(checkpoint.get('failed_files', {})):>5} files")
    print()
    
    # ChromaDB status
    print("🗄️  CHROMADB STATUS")
    print("-" * 70)
    chroma_count = get_chromadb_count()
    if isinstance(chroma_count, int):
        print(f"  Documents:   {chroma_count:>5}")
    else:
        print(f"  Status:      {chroma_count}")
    print()
    
    # Status summary
    print("=" * 70)
    if queue.get('processing'):
        print("✅ INGESTION IS RUNNING")
        print(f"   Processing {len(queue['processing'])} file(s)")
    elif queue.get('pending'):
        print("⏸️  INGESTION IS PAUSED")
        print(f"   {len(queue['pending'])} files waiting")
    elif not queue.get('pending') and queue.get('completed'):
        print("✅ INGESTION COMPLETE")
        print(f"   All {len(queue['completed'])} files processed")
    else:
        print("⚠️  NO QUEUE FOUND")
        print("   Run: python3 ingestion/generate_file_queue.py")
    print("=" * 70)


if __name__ == "__main__":
    main()

