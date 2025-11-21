#!/usr/bin/env python3
"""
Remove duplicate documents from ChromaDB collection.
Identifies duplicates by file_source and content, keeps only one copy.
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
    print("REMOVE DUPLICATES FROM CHROMADB")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)
        
        total_count = collection.count()
        print(f"Total documents: {total_count}")
        
        if total_count == 0:
            print("No documents to check.")
            return 0
        
        # Get all documents
        print("\nLoading all documents...")
        all_docs = collection.get(limit=total_count)
        
        # Group by file_source and content hash
        file_groups = defaultdict(list)
        content_seen = set()
        duplicates_to_remove = []
        
        print("Analyzing for duplicates...")
        for i, (doc_id, metadata, content) in enumerate(zip(
            all_docs.get('ids', []),
            all_docs.get('metadatas', []),
            all_docs.get('documents', [])
        )):
            if not metadata:
                continue
            
            file_source = metadata.get('file_source', '')
            original_file = metadata.get('original_file', '')
            
            # Use file_source or original_file as key
            file_key = file_source or original_file or 'unknown'
            
            # Create content hash for exact duplicate detection
            content_hash = hash(content)
            
            # Check for exact content duplicates
            if content_hash in content_seen:
                duplicates_to_remove.append(doc_id)
                print(f"  Found duplicate content: {doc_id[:20]}... ({file_key})")
            else:
                content_seen.add(content_hash)
                file_groups[file_key].append({
                    'id': doc_id,
                    'metadata': metadata,
                    'content': content
                })
        
        # Find duplicates by file_source with same section
        print("\nChecking for file_source duplicates...")
        for file_key, docs in file_groups.items():
            if len(docs) > 1:
                # Group by section to find duplicates
                section_groups = defaultdict(list)
                for doc in docs:
                    section = doc['metadata'].get('section', '')
                    section_groups[section].append(doc)
                
                # For each section with multiple docs, keep first, mark others as duplicates
                for section, section_docs in section_groups.items():
                    if len(section_docs) > 1:
                        # Keep the first one, mark others as duplicates
                        for doc in section_docs[1:]:
                            duplicates_to_remove.append(doc['id'])
                            print(f"  Found duplicate: {file_key} / {section} (keeping first, removing: {doc['id'][:20]}...)")
        
        if not duplicates_to_remove:
            print("\n✓ No duplicates found!")
            return 0
        
        print(f"\nFound {len(duplicates_to_remove)} duplicate documents to remove")
        print()
        
        # Ask for confirmation (in automated mode, proceed)
        print("Removing duplicates...")
        
        # Remove in batches
        batch_size = 100
        removed_count = 0
        
        for i in range(0, len(duplicates_to_remove), batch_size):
            batch = duplicates_to_remove[i:i + batch_size]
            try:
                collection.delete(ids=batch)
                removed_count += len(batch)
                print(f"  Removed {removed_count}/{len(duplicates_to_remove)} duplicates...")
            except Exception as e:
                print(f"  Error removing batch: {e}")
        
        # Verify final count
        final_count = collection.count()
        print()
        print("=" * 70)
        print("DEDUPLICATION COMPLETE")
        print("=" * 70)
        print(f"Original documents: {total_count}")
        print(f"Duplicates removed: {len(duplicates_to_remove)}")
        print(f"Final documents: {final_count}")
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

