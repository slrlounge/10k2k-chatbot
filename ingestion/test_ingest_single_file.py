#!/usr/bin/env python3
"""
Test script to ingest a single file directly (bypasses queue).
Usage: python3 ingestion/test_ingest_single_file.py <file_path>
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import tiktoken

load_dotenv()

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))

def split_text_semantic(text: str, max_tokens: int = 1000, overlap_tokens: int = 200) -> list:
    """Split text at semantic boundaries (paragraphs, sentences)."""
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if current_tokens + para_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))
            # Start new chunk with overlap
            overlap_text = '\n\n'.join(current_chunk[-2:]) if len(current_chunk) >= 2 else current_chunk[-1] if current_chunk else ''
            overlap_tokens_count = count_tokens(overlap_text)
            if overlap_tokens_count <= overlap_tokens:
                current_chunk = [overlap_text, para]
                current_tokens = overlap_tokens_count + para_tokens
            else:
                current_chunk = [para]
                current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks if chunks else [text]

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingestion/test_ingest_single_file.py <file_path>")
        print(f"\nExample:")
        print(f"  python3 ingestion/test_ingest_single_file.py /app/10K2Kv2/01_STEP\\ ONE/00-S1-ALL-IN-ONE_01.txt")
        return 1
    
    file_path = Path(sys.argv[1])
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return 1
    
    print("=" * 70)
    print("TEST SINGLE FILE INGESTION")
    print("=" * 70)
    print(f"File: {file_path}")
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    # Read file
    print(f"Reading file...")
    try:
        content = file_path.read_text(encoding='utf-8')
        file_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        total_tokens = count_tokens(content)
        print(f"  File size: {file_size_mb:.2f} MB")
        print(f"  Total tokens: {total_tokens}")
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return 1
    
    # Split into chunks if needed
    MAX_CHUNK_TOKENS = 1000
    CHUNK_OVERLAP = 200
    
    if total_tokens > MAX_CHUNK_TOKENS:
        print(f"Splitting into chunks (max {MAX_CHUNK_TOKENS} tokens each, {CHUNK_OVERLAP} token overlap)...")
        chunks = split_text_semantic(content, MAX_CHUNK_TOKENS, CHUNK_OVERLAP)
        print(f"Created {len(chunks)} chunks")
    else:
        chunks = [content]
    
    # Connect to ChromaDB
    print(f"\nConnecting to ChromaDB...")
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("✗ OPENAI_API_KEY not set")
            return 1
        
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        print(f"  ✓ Connected to ChromaDB")
    except Exception as e:
        print(f"✗ Error connecting to ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Ingest chunks
    print(f"\nIngesting {len(chunks)} chunk(s)...")
    try:
        for i, chunk in enumerate(chunks, 1):
            print(f"  Processing chunk {i}/{len(chunks)}...")
            
            # Create document with metadata
            doc = Document(
                page_content=chunk,
                metadata={
                    "file_source": str(file_path.relative_to(TRANSCRIPTS_DIR) if file_path.is_relative_to(TRANSCRIPTS_DIR) else file_path.name),
                    "section": f"chunk_{i}",
                    "original_file": file_path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            )
            
            vectorstore.add_documents([doc])
            print(f"    ✓ Chunk {i} ingested")
        
        print(f"\n✓ Successfully ingested: {file_path}")
        print(f"  Total chunks: {len(chunks)}")
        
        # Verify
        count = vectorstore._collection.count()
        print(f"\nCollection now has {count} document(s)")
        
    except Exception as e:
        print(f"✗ Error ingesting: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

