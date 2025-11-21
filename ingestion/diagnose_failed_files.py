#!/usr/bin/env python3
"""
Diagnostic script to check file sizes and ChromaDB status
Helps identify which files are actually causing OOM errors
"""

import os
import sys
from pathlib import Path
import json
import chromadb

# Configuration
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2K v2'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

# Checkpoint paths
checkpoint_paths = [
    Path('/app/checkpoints/ingest_transcripts.json'),
    Path('checkpoints/ingest_transcripts.json'),
    Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_transcripts.json'))
]

print("=" * 70)
print("DIAGNOSTIC: FILE SIZES & CHROMADB STATUS")
print("=" * 70)
print()

# 1. Load checkpoint
print("1. Loading checkpoint...")
processed_files = set()
checkpoint_file = None

for cp_path in checkpoint_paths:
    if cp_path.exists():
        try:
            with open(cp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                processed_files = set(data.get('processed', []))
                checkpoint_file = cp_path
                print(f"   ✓ Loaded from: {cp_path}")
                print(f"   Processed files: {len(processed_files)}")
                break
        except Exception as e:
            print(f"   ⚠️  Error reading {cp_path}: {e}")
            continue

if not checkpoint_file:
    print("   ⚠️  No checkpoint found")

print()

# 2. Find all transcript files
print("2. Scanning transcript files...")
all_files = []
if TRANSCRIPTS_DIR.exists():
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            try:
                file_size_mb = txt_file.stat().st_size / (1024 * 1024)
                all_files.append((txt_file, file_size_mb))
            except Exception as e:
                print(f"   ⚠️  Error checking {txt_file.name}: {e}")

all_files.sort(key=lambda x: x[1], reverse=True)  # Sort by size, largest first
print(f"   Found {len(all_files)} total transcript files")
print()

# 3. Identify failed files
print("3. Identifying failed files...")
all_file_paths = {str(f[0]) for f in all_files}
failed_files = all_file_paths - processed_files
print(f"   Failed/unprocessed files: {len(failed_files)}")
print()

# 4. Check file sizes
print("4. File size analysis:")
print("   " + "-" * 66)
print(f"   {'Size (MB)':<12} {'Status':<15} {'Filename'}")
print("   " + "-" * 66)

size_ranges = {
    '>10MB': 0,
    '5-10MB': 0,
    '1-5MB': 0,
    '0.25-1MB': 0,
    '<0.25MB': 0
}

failed_large_files = []

for file_path, file_size_mb in all_files:
    file_str = str(file_path)
    status = "PROCESSED" if file_str in processed_files else "FAILED"
    
    # Categorize by size
    if file_size_mb > 10:
        size_ranges['>10MB'] += 1
        size_cat = '>10MB'
    elif file_size_mb > 5:
        size_ranges['5-10MB'] += 1
        size_cat = '5-10MB'
    elif file_size_mb > 1:
        size_ranges['1-5MB'] += 1
        size_cat = '1-5MB'
    elif file_size_mb > 0.25:
        size_ranges['0.25-1MB'] += 1
        size_cat = '0.25-1MB'
    else:
        size_ranges['<0.25MB'] += 1
        size_cat = '<0.25MB'
    
    # Show failed files >0.25MB
    if status == "FAILED" and file_size_mb > 0.25:
        failed_large_files.append((file_path, file_size_mb))
        print(f"   {file_size_mb:>10.2f}MB  {status:<15} {file_path.name}")

print("   " + "-" * 66)
print()

# 5. Size distribution
print("5. Size distribution:")
for size_range, count in size_ranges.items():
    print(f"   {size_range:>12}: {count} files")
print()

# 6. Failed large files summary
print("6. Failed large files (>0.25MB):")
if failed_large_files:
    print(f"   Found {len(failed_large_files)} failed files >0.25MB")
    print("   These need to be split:")
    for file_path, file_size_mb in failed_large_files[:10]:  # Show first 10
        print(f"     - {file_path.name}: {file_size_mb:.2f}MB")
    if len(failed_large_files) > 10:
        print(f"     ... and {len(failed_large_files) - 10} more")
else:
    print("   ✓ No failed files >0.25MB found")
    print("   All failed files are small enough to ingest")
print()

# 7. Check ChromaDB
print("7. Checking ChromaDB...")
try:
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_collection(name=COLLECTION_NAME)
    count = collection.count()
    print(f"   ✓ Connected to ChromaDB")
    print(f"   Documents in collection: {count}")
    print(f"   Estimated files: ~{count // 20} (assuming ~20 chunks per file)")
except Exception as e:
    print(f"   ✗ Error connecting to ChromaDB: {e}")
print()

# 8. Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total transcript files: {len(all_files)}")
print(f"Processed (checkpoint): {len(processed_files)}")
print(f"Failed/unprocessed: {len(failed_files)}")
print(f"Failed files >0.25MB: {len(failed_large_files)}")
print()

if failed_large_files:
    print("⚠️  ACTION NEEDED:")
    print(f"   {len(failed_large_files)} failed files need recursive splitting")
    print("   Run the recursive splitting script to process them")
else:
    print("✅ NO ACTION NEEDED:")
    print("   All failed files are small enough (<0.25MB)")
    print("   They should ingest without splitting")
    print("   Check why they failed (may be other issues)")

print("=" * 70)

