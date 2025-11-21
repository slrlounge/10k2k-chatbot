#!/usr/bin/env python3
"""
Ingest Pre-Split Files
Ingests all pre-split segment files (e.g., sales_01.txt, sales_02.txt) into ChromaDB.
Assumes files have already been split locally using split_files_locally.py
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List

# Configuration
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2K v2'))
INGEST_SCRIPT = Path('/app/ingestion/ingest_single_transcript_ultra_minimal.py')
PYTHON_CMD = os.getenv('PYTHON_CMD', 'python3')

stats = {
    'files_found': 0,
    'files_processed': 0,
    'files_succeeded': 0,
    'files_failed': []
}


def find_all_segment_files() -> List[Path]:
    """Find all segment files (files with _XX pattern) and regular files."""
    all_files = []
    
    if not TRANSCRIPTS_DIR.exists():
        print(f"✗ Error: Directory '{TRANSCRIPTS_DIR}' does not exist!")
        return []
    
    # Find all .txt files
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            all_files.append(txt_file)
    
    # Sort by directory and filename for logical processing order
    all_files.sort(key=lambda p: (str(p.parent), p.name))
    
    return all_files


def ingest_file(file_path: Path) -> bool:
    """Ingest a single file segment."""
    try:
        result = subprocess.run(
            [PYTHON_CMD, str(INGEST_SCRIPT), str(file_path)],
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"  ✗ Failed (exit {result.returncode})")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main orchestration function."""
    print("=" * 70)
    print("INGEST PRE-SPLIT FILES INTO CHROMADB")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Source directory: {TRANSCRIPTS_DIR}")
    print()
    
    # Find all files
    print("Scanning for files...")
    all_files = find_all_segment_files()
    stats['files_found'] = len(all_files)
    print(f"Found {len(all_files)} files to process")
    print()
    
    if not all_files:
        print("No files found!")
        return 0
    
    # Process each file
    print("=" * 70)
    print("PROCESSING FILES")
    print("=" * 70)
    print()
    
    for i, file_path in enumerate(all_files, 1):
        relative_path = file_path.relative_to(TRANSCRIPTS_DIR)
        print(f"[{i}/{len(all_files)}] {relative_path}")
        
        if ingest_file(file_path):
            print(f"  ✓ Successfully ingested")
            stats['files_succeeded'] += 1
        else:
            print(f"  ✗ Failed to ingest")
            stats['files_failed'].append(str(relative_path))
        
        stats['files_processed'] += 1
        print()
    
    # Print summary
    print("=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Files found: {stats['files_found']}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files succeeded: {stats['files_succeeded']}")
    print(f"Files failed: {len(stats['files_failed'])}")
    
    if stats['files_failed']:
        print(f"\n⚠️  Failed files:")
        for failed_file in stats['files_failed'][:10]:  # Show first 10
            print(f"  - {failed_file}")
        if len(stats['files_failed']) > 10:
            print(f"  ... and {len(stats['files_failed']) - 10} more")
    else:
        print("\n✅ All files successfully ingested!")
    
    print("=" * 70)
    
    return 0 if not stats['files_failed'] else 1


if __name__ == "__main__":
    sys.exit(main())

