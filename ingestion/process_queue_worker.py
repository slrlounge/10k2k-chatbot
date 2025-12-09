#!/usr/bin/env python3
"""
Queue Processing Worker
Runs ingest_one_file.py repeatedly until queue is empty.
Designed to be called by Render cron or manual execution.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
INGEST_SCRIPT = Path('/app/ingestion/ingest_one_file.py')
PYTHON_CMD = os.getenv('PYTHON_CMD', 'python3')
MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', '1'))  # Process 1 file per run by default


def load_queue() -> dict:
    """Load queue to check status."""
    if not QUEUE_FILE.exists():
        return {"pending": [], "processing": [], "completed": [], "failed": []}
    
    try:
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"pending": [], "processing": [], "completed": [], "failed": []}


def run_ingestion() -> bool:
    """Run single file ingestion."""
    try:
        result = subprocess.run(
            [PYTHON_CMD, str(INGEST_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per file
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Ingestion timed out")
        return False
    except Exception as e:
        print(f"Error running ingestion: {e}")
        return False


def main():
    """Main worker loop."""
    print("=" * 70)
    print("QUEUE PROCESSING WORKER")
    print("=" * 70)
    print(f"Queue file: {QUEUE_FILE}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print()
    
    # Check queue status
    queue = load_queue()
    pending_count = len(queue.get("pending", []))
    
    print(f"Pending files: {pending_count}")
    print(f"Completed: {len(queue.get('completed', []))}")
    print(f"Failed: {len(queue.get('failed', []))}")
    print()
    
    if pending_count == 0:
        print("No pending files. Queue is empty.")
        return 0
    
    # Process files
    processed = 0
    for i in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {i+1}/{MAX_ITERATIONS} ---")
        
        # Check if queue still has files
        queue = load_queue()
        if not queue.get("pending"):
            print("Queue is now empty.")
            break
        
        # Run ingestion
        success = run_ingestion()
        processed += 1
        
        if not success:
            print(f"Iteration {i+1} failed")
            # Continue anyway - let next run retry
        
        # Small delay to allow cleanup
        time.sleep(2)
    
    # Final status
    queue = load_queue()
    print("\n" + "=" * 70)
    print("FINAL STATUS")
    print("=" * 70)
    print(f"Processed this run: {processed}")
    print(f"Remaining pending: {len(queue.get('pending', []))}")
    print(f"Total completed: {len(queue.get('completed', []))}")
    print(f"Total failed: {len(queue.get('failed', []))}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

