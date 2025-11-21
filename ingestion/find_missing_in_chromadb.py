#!/usr/bin/env python3
"""
Find files that are NOT actually in ChromaDB (even if marked as processed)
This identifies files that need to be re-ingested
"""

import os
import sys
from pathlib import Path
import json
import chromadb

# Configuration
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

print("=" * 70)
print("FINDING FILES MISSING FROM CHROMADB")
print("=" * 70)
print()

# 1. Connect to ChromaDB
print("1. Connecting to ChromaDB...")
try:
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_collection(name=COLLECTION_NAME)
    total_docs = collection.count()
    print(f"   ✓ Connected to ChromaDB")
    print(f"   Total documents in collection: {total_docs}")
except Exception as e:
    print(f"   ✗ Error connecting to ChromaDB: {e}")
    sys.exit(1)
print()

# 2. Get all unique filenames from ChromaDB
print("2. Getting filenames from ChromaDB...")
try:
    # Get all documents (in batches if needed)
    chromadb_filenames = set()
    batch_size = 1000
    
    # Get metadata for all documents
    all_results = collection.get(limit=total_docs if total_docs < 10000 else 10000)
    
    if all_results and all_results.get('metadatas'):
        for metadata in all_results['metadatas']:
            if metadata and 'filename' in metadata:
                # Extract base filename (remove _01, _02 suffixes)
                filename = metadata['filename']
                # Remove segment suffixes (e.g., "file_01.txt" -> "file.txt")
                base_filename = filename.rsplit('_', 1)[0] if '_' in filename and filename.rsplit('_', 1)[1].replace('.txt', '').isdigit() else filename
                chromadb_filenames.add(base_filename)
    
    print(f"   Found {len(chromadb_filenames)} unique files in ChromaDB")
    if len(chromadb_filenames) > 0:
        print("   Sample files in ChromaDB:")
        for fname in list(chromadb_filenames)[:5]:
            print(f"     - {fname}")
        if len(chromadb_filenames) > 5:
            print(f"     ... and {len(chromadb_filenames) - 5} more")
except Exception as e:
    print(f"   ⚠️  Error getting filenames: {e}")
    chromadb_filenames = set()
print()

# 3. Find all transcript files
print("3. Scanning transcript files...")
all_transcript_files = []
if TRANSCRIPTS_DIR.exists():
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            try:
                file_size_mb = txt_file.stat().st_size / (1024 * 1024)
                all_transcript_files.append((txt_file, file_size_mb))
            except Exception as e:
                print(f"   ⚠️  Error checking {txt_file.name}: {e}")

print(f"   Found {len(all_transcript_files)} total transcript files")
print()

# 4. Find missing files
print("4. Identifying files missing from ChromaDB...")
missing_files = []
missing_large_files = []

for file_path, file_size_mb in all_transcript_files:
    filename = file_path.name
    
    # Check if file is in ChromaDB
    if filename not in chromadb_filenames:
        missing_files.append((file_path, file_size_mb))
        if file_size_mb > 0.25:  # Files >0.25MB that are missing
            missing_large_files.append((file_path, file_size_mb))

print(f"   Files missing from ChromaDB: {len(missing_files)}")
print(f"   Missing files >0.25MB: {len(missing_large_files)}")
print()

# 5. Show missing large files
if missing_large_files:
    print("5. Missing large files (>0.25MB) that need splitting:")
    print("   " + "-" * 66)
    print(f"   {'Size (MB)':<12} {'Filename'}")
    print("   " + "-" * 66)
    
    # Sort by size, largest first
    missing_large_files.sort(key=lambda x: x[1], reverse=True)
    
    for file_path, file_size_mb in missing_large_files:
        print(f"   {file_size_mb:>10.2f}MB  {file_path.name}")
    
    print("   " + "-" * 66)
    print()
else:
    print("5. No missing large files found")
    print("   All missing files are <0.25MB")
    print()

# 6. Show all missing files (if needed)
if missing_files and len(missing_files) <= 20:
    print("6. All missing files:")
    for file_path, file_size_mb in missing_files:
        status = "LARGE" if file_size_mb > 0.25 else "small"
        print(f"   {file_path.name} ({file_size_mb:.2f}MB) - {status}")
elif missing_files:
    print(f"6. Showing first 20 of {len(missing_files)} missing files:")
    for file_path, file_size_mb in missing_files[:20]:
        status = "LARGE" if file_size_mb > 0.25 else "small"
        print(f"   {file_path.name} ({file_size_mb:.2f}MB) - {status}")
    print(f"   ... and {len(missing_files) - 20} more")
print()

# 7. Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total transcript files: {len(all_transcript_files)}")
print(f"Files in ChromaDB: {len(chromadb_filenames)}")
print(f"Files missing from ChromaDB: {len(missing_files)}")
print(f"Missing files >0.25MB: {len(missing_large_files)}")
print()

if missing_large_files:
    print("⚠️  ACTION NEEDED:")
    print(f"   {len(missing_large_files)} large files are missing from ChromaDB")
    print("   These need recursive splitting and ingestion")
    print("   Run the recursive splitting script to process them")
else:
    print("✅ NO LARGE FILES MISSING:")
    print("   All missing files are <0.25MB")
    if missing_files:
        print(f"   {len(missing_files)} small files are missing")
        print("   They should ingest without splitting")
        print("   Check why they're not ingesting (may be other issues)")

print("=" * 70)

