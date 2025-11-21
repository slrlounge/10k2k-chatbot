#!/usr/bin/env python3
"""
Show detailed information about what has been ingested into ChromaDB.
"""

import os
from dotenv import load_dotenv
import chromadb
from collections import defaultdict

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def main():
    print("=" * 70)
    print("CHROMADB INGESTION REPORT")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)
        
        total_count = collection.count()
        print(f"📊 Total Documents: {total_count}")
        print()
        
        if total_count == 0:
            print("⚠️  No documents found in collection.")
            print("   Run ingestion to add documents:")
            print("   python3 ingestion/generate_file_queue.py")
            print("   python3 ingestion/process_queue_worker.py")
            return 0
        
        # Get all documents (in batches if needed)
        print("📋 Fetching document metadata...")
        all_docs = collection.get(limit=total_count)
        
        # Group by original file
        file_stats = defaultdict(lambda: {"chunks": 0, "sections": set()})
        
        for i, metadata in enumerate(all_docs.get('metadatas', [])):
            if metadata:
                original_file = metadata.get('original_file', 'unknown')
                section = metadata.get('section', 'unknown')
                file_source = metadata.get('file_source', original_file)
                
                file_stats[original_file]["chunks"] += 1
                file_stats[original_file]["sections"].add(section)
                file_stats[original_file]["file_source"] = file_source
        
        # Display statistics
        print()
        print("=" * 70)
        print("FILE INGESTION SUMMARY")
        print("=" * 70)
        print(f"Unique Files: {len(file_stats)}")
        print(f"Total Chunks: {total_count}")
        print()
        
        # Show files grouped by directory
        files_by_dir = defaultdict(list)
        for filename, stats in sorted(file_stats.items()):
            file_source = stats.get('file_source', filename)
            # Extract directory from file_source
            if '/' in file_source:
                directory = '/'.join(file_source.split('/')[:-1])
            else:
                directory = 'root'
            files_by_dir[directory].append((filename, stats))
        
        # Display by directory
        for directory in sorted(files_by_dir.keys()):
            print(f"\n📁 {directory}/")
            print("-" * 70)
            for filename, stats in sorted(files_by_dir[directory]):
                chunks = stats['chunks']
                sections = len(stats['sections'])
                print(f"  ✓ {filename}")
                print(f"    └─ {chunks} chunk(s), {sections} section(s)")
        
        # Show sample documents
        print()
        print("=" * 70)
        print("SAMPLE DOCUMENTS (first 3)")
        print("=" * 70)
        sample_docs = collection.get(limit=3)
        for i, (doc_id, metadata, content) in enumerate(zip(
            sample_docs.get('ids', []),
            sample_docs.get('metadatas', []),
            sample_docs.get('documents', [])
        ), 1):
            print(f"\n[{i}] ID: {doc_id}")
            if metadata:
                print(f"    File: {metadata.get('original_file', 'unknown')}")
                print(f"    Section: {metadata.get('section', 'unknown')}")
                print(f"    Source: {metadata.get('file_source', 'unknown')}")
            if content:
                preview = content[:200].replace('\n', ' ')
                print(f"    Preview: {preview}...")
        
        # Summary statistics
        print()
        print("=" * 70)
        print("STATISTICS")
        print("=" * 70)
        chunks_per_file = [stats['chunks'] for stats in file_stats.values()]
        if chunks_per_file:
            avg_chunks = sum(chunks_per_file) / len(chunks_per_file)
            max_chunks = max(chunks_per_file)
            min_chunks = min(chunks_per_file)
            print(f"Average chunks per file: {avg_chunks:.1f}")
            print(f"Max chunks in a file: {max_chunks}")
            print(f"Min chunks in a file: {min_chunks}")
        
        print()
        print("=" * 70)
        print("✓ REPORT COMPLETE")
        print("=" * 70)
        
    except chromadb.errors.NotFoundError:
        print(f"✗ Collection '{COLLECTION_NAME}' does not exist.")
        print("  Run ingestion to create the collection.")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

