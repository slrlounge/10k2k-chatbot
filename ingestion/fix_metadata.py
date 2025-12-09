#!/usr/bin/env python3
"""
Fix missing metadata in ChromaDB documents.
This script checks all documents and updates missing filename/type metadata.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from collections import defaultdict

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
CHROMA_URL = os.getenv('CHROMA_URL', None)
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

def extract_filename_from_id(doc_id: str) -> str:
    """Extract filename from document ID if it follows a pattern."""
    # Pattern: "filename_chunkindex" or "filename-chunkindex"
    if '_' in doc_id:
        parts = doc_id.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
    elif '-' in doc_id:
        parts = doc_id.rsplit('-', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
    return None

def infer_type_from_filename(filename: str) -> str:
    """Infer document type from filename."""
    filename_lower = filename.lower()
    if 'transcript' in filename_lower:
        return 'transcript'
    elif filename_lower.endswith('.pdf'):
        return 'pdf'
    elif filename_lower.endswith('.txt'):
        return 'text'
    elif filename_lower.endswith('.md'):
        return 'markdown'
    else:
        return 'document'

def clean_filename(filename: str) -> str:
    """Extract just the filename from a path."""
    if '/' in filename:
        return filename.split('/')[-1]
    elif '\\' in filename:
        return filename.split('\\')[-1]
    return filename

def main():
    print("=" * 70)
    print("FIX METADATA IN CHROMADB")
    print("=" * 70)
    
    try:
        # Connect to ChromaDB
        if CHROMA_URL:
            url = CHROMA_URL.replace('http://', '').replace('https://', '')
            if ':' in url:
                host, port = url.split(':')
                port = int(port)
            else:
                host = url
                port = 8000
            print(f"Connecting to: {host}:{port}")
            client = chromadb.HttpClient(host=host, port=port)
        else:
            print(f"Connecting to: {CHROMA_HOST}:{CHROMA_PORT}")
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        collection = client.get_collection(COLLECTION_NAME)
        total_count = collection.count()
        
        print(f"Total documents: {total_count}")
        print()
        
        if total_count == 0:
            print("No documents found!")
            return 0
        
        # Get all documents
        print("Fetching all documents...")
        all_data = collection.get(limit=total_count)
        
        ids = all_data.get('ids', [])
        metadatas = all_data.get('metadatas', [])
        
        if not ids:
            print("No document IDs found!")
            return 1
        
        print(f"Found {len(ids)} documents to check\n")
        
        # Track what needs updating
        updates_needed = []
        stats = {
            'has_filename': 0,
            'missing_filename': 0,
            'has_type': 0,
            'missing_type': 0,
            'will_update': 0
        }
        
        # Check each document
        for i, (doc_id, metadata) in enumerate(zip(ids, metadatas)):
            if i % 100 == 0:
                print(f"  Checking document {i+1}/{len(ids)}...")
            
            metadata = metadata or {}
            needs_update = False
            updated_metadata = metadata.copy()
            
            # Check filename
            filename = (
                metadata.get('filename') or
                metadata.get('file_source') or
                metadata.get('original_file') or
                metadata.get('source')
            )
            
            if filename and isinstance(filename, str) and filename.strip():
                stats['has_filename'] += 1
                filename = clean_filename(filename.strip())
            else:
                stats['missing_filename'] += 1
                # Try to extract from ID
                extracted = extract_filename_from_id(doc_id)
                if extracted:
                    filename = extracted
                    needs_update = True
                else:
                    filename = None
            
            # Check type
            doc_type = metadata.get('type')
            if doc_type and isinstance(doc_type, str) and doc_type.strip():
                stats['has_type'] += 1
            else:
                stats['missing_type'] += 1
                # Infer from filename
                if filename:
                    doc_type = infer_type_from_filename(filename)
                    needs_update = True
                else:
                    doc_type = 'document'
                    needs_update = True
            
            # Update metadata if needed
            if needs_update or not filename:
                if filename:
                    updated_metadata['filename'] = filename
                if doc_type:
                    updated_metadata['type'] = doc_type
                
                updates_needed.append({
                    'id': doc_id,
                    'metadata': updated_metadata
                })
                stats['will_update'] += 1
        
        # Print statistics
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        print(f"Documents with filename: {stats['has_filename']}")
        print(f"Documents missing filename: {stats['missing_filename']}")
        print(f"Documents with type: {stats['has_type']}")
        print(f"Documents missing type: {stats['missing_type']}")
        print(f"Documents that need update: {stats['will_update']}")
        print()
        
        if not updates_needed:
            print("✓ All documents have proper metadata!")
            return 0
        
        # Ask for confirmation
        print("=" * 70)
        print(f"READY TO UPDATE {len(updates_needed)} DOCUMENTS")
        print("=" * 70)
        print("\nThis will update metadata for documents missing filename or type.")
        response = input("\nProceed with update? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("Update cancelled.")
            return 0
        
        # Perform updates in batches
        print(f"\nUpdating {len(updates_needed)} documents...")
        batch_size = 100
        updated = 0
        
        for i in range(0, len(updates_needed), batch_size):
            batch = updates_needed[i:i+batch_size]
            batch_ids = [item['id'] for item in batch]
            batch_metadatas = [item['metadata'] for item in batch]
            
            try:
                collection.update(
                    ids=batch_ids,
                    metadatas=batch_metadatas
                )
                updated += len(batch)
                print(f"  Updated batch {i//batch_size + 1}: {updated}/{len(updates_needed)} documents")
            except Exception as e:
                print(f"  ✗ Error updating batch {i//batch_size + 1}: {e}")
                continue
        
        print("\n" + "=" * 70)
        print(f"✓ UPDATE COMPLETE: {updated}/{len(updates_needed)} documents updated")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

