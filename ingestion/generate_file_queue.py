#!/usr/bin/env python3
"""
Generate File Queue
Scans transcript directory and creates a queue JSON file for ingestion.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))


def load_checkpoint() -> dict:
    """Load checkpoint to skip already processed files."""
    if not CHECKPOINT_FILE.exists():
        return {"processed_files": {}, "failed_files": {}}
    
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"processed_files": {}, "failed_files": {}}


def find_all_txt_files() -> list:
    """Find all .txt files in transcript directory."""
    files = []
    
    if not TRANSCRIPTS_DIR.exists():
        print(f"Error: Directory '{TRANSCRIPTS_DIR}' does not exist!")
        return files
    
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            files.append(txt_file)
    
    # Sort for consistent ordering
    files.sort(key=lambda p: (str(p.parent), p.name))
    
    return files


def generate_queue():
    """Generate file queue excluding already processed files."""
    print("=" * 70)
    print("GENERATING FILE QUEUE")
    print("=" * 70)
    print(f"Source directory: {TRANSCRIPTS_DIR}")
    print(f"Queue file: {QUEUE_FILE}")
    print()
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    processed = set(checkpoint.get("processed_files", {}).keys())
    
    # Find all files
    print("Scanning for files...")
    all_files = find_all_txt_files()
    print(f"Found {len(all_files)} total files")
    
    # Filter out already processed
    pending_files = []
    for file_path in all_files:
        file_str = str(file_path)
        if file_str not in processed:
            pending_files.append(file_str)
    
    print(f"Pending files: {len(pending_files)}")
    print(f"Already processed: {len(processed)}")
    print()
    
    # Create queue structure
    queue = {
        "pending": pending_files,
        "processing": [],
        "completed": list(processed),
        "failed": list(checkpoint.get("failed_files", {}).keys())
    }
    
    # Save queue
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)
    
    print(f"✓ Queue saved to: {QUEUE_FILE}")
    print(f"  Pending: {len(queue['pending'])}")
    print(f"  Completed: {len(queue['completed'])}")
    print(f"  Failed: {len(queue['failed'])}")
    print()
    
    return queue


if __name__ == "__main__":
    generate_queue()

