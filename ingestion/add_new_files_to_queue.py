#!/usr/bin/env python3
"""
Add only new files to the queue by checking against ChromaDB.
Skips files that are already ingested.
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


def get_ingested_files_from_chromadb():
    """Get set of files that are already in ChromaDB."""
    ingested_files = set()
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)
        
        # Get all documents (in batches if needed)
        count = collection.count()
        if count == 0:
            return ingested_files
        
        # Get all metadata
        all_docs = collection.get(limit=count)
        
        for metadata in all_docs.get('metadatas', []):
            if metadata:
                # Check different metadata fields
                file_source = metadata.get('file_source', '')
                original_file = metadata.get('original_file', '')
                
                # Add both full paths and filenames
                if file_source:
                    ingested_files.add(file_source)
                    # Also add just the filename for matching
                    if '/' in file_source:
                        ingested_files.add(Path(file_source).name)
                    else:
                        ingested_files.add(file_source)
                
                if original_file:
                    ingested_files.add(original_file)
                    # Also add just the filename
                    ingested_files.add(Path(original_file).name)
        
        print(f"  Found {len(ingested_files)} unique files already in ChromaDB")
    except Exception as e:
        print(f"  ⚠ Warning: Could not check ChromaDB: {e}")
        print(f"  Will rely on checkpoint only")
    
    return ingested_files


def load_queue():
    """Load existing queue or create new one."""
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    return {"pending": [], "completed": [], "failed": []}


def load_checkpoint():
    """Load existing checkpoint or create new one."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"processed_files": {}, "failed_files": {}}


def is_file_ingested(file_path: Path, ingested_files: set, checkpoint: dict) -> bool:
    """Check if file is already ingested (in ChromaDB or checkpoint)."""
    filename = file_path.name
    relative_path = str(file_path.relative_to(TRANSCRIPTS_DIR))
    absolute_path = str(file_path)
    
    # Check ChromaDB by multiple methods
    if relative_path in ingested_files:
        return True
    if absolute_path in ingested_files:
        return True
    if filename in ingested_files:
        return True
    
    # Check checkpoint by multiple methods
    if absolute_path in checkpoint.get("processed_files", {}):
        return True
    if relative_path in checkpoint.get("processed_files", {}):
        return True
    
    # Check by filename in checkpoint
    for processed_file in checkpoint.get("processed_files", {}):
        if Path(processed_file).name == filename:
            return True
    
    return False


def main():
    print("=" * 70)
    print("ADD NEW FILES TO QUEUE")
    print("=" * 70)
    print(f"Source directory: {TRANSCRIPTS_DIR}")
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    # Ensure directories exist
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing queue and checkpoint
    queue = load_queue()
    checkpoint = load_checkpoint()
    
    print("Checking ChromaDB for already ingested files...")
    ingested_files = get_ingested_files_from_chromadb()
    print()
    
    # Find all .txt files
    print("Scanning for .txt files...")
    all_txt_files = sorted(TRANSCRIPTS_DIR.rglob("*.txt"))
    print(f"  Found {len(all_txt_files)} total .txt files")
    
    # Filter to only new files
    new_files = []
    skipped_files = []
    
    for txt_file in all_txt_files:
        if is_file_ingested(txt_file, ingested_files, checkpoint):
            skipped_files.append(txt_file)
        else:
            new_files.append(txt_file)
    
    print(f"  New files: {len(new_files)}")
    print(f"  Already ingested: {len(skipped_files)}")
    print()
    
    if not new_files:
        print("✓ No new files to ingest!")
        print(f"  All {len(skipped_files)} files are already ingested")
        return 0
    
    # Add new files to queue (avoid duplicates)
    existing_pending = set(queue.get("pending", []))
    added_count = 0
    
    for txt_file in new_files:
        file_str = str(txt_file)
        if file_str not in existing_pending:
            queue.setdefault("pending", []).append(file_str)
            added_count += 1
    
    # Save queue
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)
    
    print("=" * 70)
    print("QUEUE UPDATED")
    print("=" * 70)
    print(f"New files added to queue: {added_count}")
    print(f"Total pending: {len(queue.get('pending', []))}")
    print(f"Total completed: {len(queue.get('completed', []))}")
    print(f"Total failed: {len(queue.get('failed', []))}")
    print()
    print("Next step: Run ingestion worker:")
    print("  MAX_ITERATIONS=1000 python3 ingestion/process_queue_worker.py")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())

