#!/usr/bin/env python3
"""
Single-File Ingestion Pipeline for Render (4GB RAM)
Processes exactly ONE file per execution to avoid memory spikes.
Designed to be run repeatedly until queue is empty.
"""

import os
import sys
import json
import gc
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, List
import subprocess as sp
from dotenv import load_dotenv
import tiktoken
import chromadb
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()

# Configuration
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
QUEUE_FILE = Path(os.getenv('QUEUE_FILE', '/app/checkpoints/file_queue.json'))
CHECKPOINT_FILE = Path(os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_checkpoint.json'))
LOG_DIR = Path(os.getenv('LOG_DIR', '/app/logs'))
CHUNK_SIZE = 1000  # Optimal chunk size for context preservation
CHUNK_OVERLAP = 200  # 20% overlap to prevent context loss at boundaries
MAX_CHUNK_TOKENS = 1000  # Increased for better context preservation
EMBEDDING_MODEL = 'text-embedding-3-small'

# Ensure directories exist
QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")


def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def get_chroma_client():
    """Get ChromaDB client."""
    return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)


def get_collection():
    """Get or create ChromaDB collection."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return collection


def load_queue() -> Dict:
    """Load file queue from JSON."""
    default_queue = {"pending": [], "processing": [], "completed": [], "failed": []}
    
    if not QUEUE_FILE.exists():
        return default_queue
    
    try:
        queue = json.load(open(QUEUE_FILE, 'r'))
        # Ensure all required keys exist
        for key in default_queue.keys():
            if key not in queue:
                queue[key] = []
        return queue
    except Exception as e:
        print(f"Error loading queue: {e}")
        return default_queue


def save_queue(queue: Dict):
    """Save file queue to JSON."""
    try:
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"Error saving queue: {e}")


def load_checkpoint() -> Dict:
    """Load ingestion checkpoint."""
    if not CHECKPOINT_FILE.exists():
        return {"processed_files": {}, "failed_files": {}}
    
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"processed_files": {}, "failed_files": {}}


def save_checkpoint(checkpoint: Dict):
    """Save ingestion checkpoint."""
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    except Exception as e:
        print(f"Error saving checkpoint: {e}")


def get_next_file(queue: Dict) -> Optional[Path]:
    """Get next pending file from queue."""
    if not queue.get("pending"):
        return None
    
    file_path_str = queue["pending"].pop(0)
    queue["processing"].append(file_path_str)
    save_queue(queue)
    
    return Path(file_path_str)


def mark_file_complete(queue: Dict, file_path: Path, success: bool = True):
    """Mark file as completed or failed."""
    file_path_str = str(file_path)
    
    if file_path_str in queue["processing"]:
        queue["processing"].remove(file_path_str)
    
    if success:
        if file_path_str not in queue["completed"]:
            queue["completed"].append(file_path_str)
    else:
        if file_path_str not in queue["failed"]:
            queue["failed"].append(file_path_str)
    
    save_queue(queue)


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))


def split_text_semantic(text: str, max_tokens: int, overlap_tokens: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text at semantic boundaries with overlap to preserve context.
    Overlap prevents information loss at chunk boundaries, reducing hallucination.
    """
    # Try paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_tokens = 0
    overlap_buffer = []  # Store last N tokens for overlap
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if para_tokens > max_tokens:
            # Paragraph too large, split by sentences
            sentences = para.split('. ')
            for sent in sentences:
                sent_tokens = count_tokens(sent)
                
                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(chunk_text)
                    
                    # Build overlap buffer from end of current chunk
                    # Take last sentences that fit in overlap_tokens
                    overlap_buffer = []
                    overlap_token_count = 0
                    for item in reversed(current_chunk):
                        item_tokens = count_tokens(item)
                        if overlap_token_count + item_tokens <= overlap_tokens:
                            overlap_buffer.insert(0, item)
                            overlap_token_count += item_tokens
                        else:
                            break
                    
                    # Start new chunk with overlap
                    current_chunk = overlap_buffer + [sent]
                    current_tokens = overlap_token_count + sent_tokens
                else:
                    current_chunk.append(sent)
                    current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
                
                # Build overlap buffer
                overlap_buffer = []
                overlap_token_count = 0
                for item in reversed(current_chunk):
                    item_tokens = count_tokens(item)
                    if overlap_token_count + item_tokens <= overlap_tokens:
                        overlap_buffer.insert(0, item)
                        overlap_token_count += item_tokens
                    else:
                        break
                
                # Start new chunk with overlap
                current_chunk = overlap_buffer + [para]
                current_tokens = overlap_token_count + para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def ingest_file_chunks(file_path: Path, chunks: List[str], openai_client: OpenAI, collection) -> bool:
    """Ingest file chunks into ChromaDB."""
    try:
        # Generate embeddings
        embeddings = []
        documents = []
        ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            # Get embedding from OpenAI
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=chunk
            )
            embedding = response.data[0].embedding
            
            # Create metadata
            relative_path = file_path.relative_to(TRANSCRIPTS_DIR)
            # Infer type from file extension
            file_ext = file_path.suffix.lower()
            doc_type = 'transcript' if 'transcript' in str(relative_path).lower() else (
                'pdf' if file_ext == '.pdf' else
                'text' if file_ext == '.txt' else
                'document'
            )
            metadata = {
                "filename": file_path.name,  # Add filename for consistency
                "file_source": str(relative_path),
                "original_file": str(relative_path),
                "type": doc_type,  # Add type field
                "section": f"chunk_{i+1}",
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            
            doc_id = f"{relative_path}_{i}"
            
            embeddings.append(embedding)
            documents.append(chunk)
            ids.append(doc_id)
            metadatas.append(metadata)
        
        # Batch add to ChromaDB (small batches to avoid memory issues)
        batch_size = 10
        for i in range(0, len(embeddings), batch_size):
            batch_embeddings = embeddings[i:i+batch_size]
            batch_documents = documents[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            collection.add(
                embeddings=batch_embeddings,
                documents=batch_documents,
                ids=batch_ids,
                metadatas=batch_metadatas
            )
            
            # Force garbage collection after each batch
            del batch_embeddings, batch_documents, batch_ids, batch_metadatas
            gc.collect()
        
        return True
        
    except Exception as e:
        print(f"Error ingesting chunks: {e}")
        traceback.print_exc()
        return False


def auto_split_file(file_path: Path) -> List[Path]:
    """Automatically split a file that failed ingestion."""
    print(f"Attempting to auto-split file: {file_path}")
    
    try:
        # Call auto_chunker.py
        result = sp.run(
            [sys.executable, str(Path(__file__).parent / 'auto_chunker.py'), str(file_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # Find created segments
            segments = []
            base_name = file_path.stem
            parent = file_path.parent
            
            # Look for segment files
            for i in range(1, 100):  # Max 100 segments
                segment_name = f"{base_name}_{i:02d}{file_path.suffix}"
                segment_path = parent / segment_name
                if segment_path.exists():
                    segments.append(segment_path)
                else:
                    break
            
            if segments:
                print(f"✓ Created {len(segments)} segments")
                return segments
            else:
                print("✗ No segments created")
                return []
        else:
            print(f"✗ Auto-split failed: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"✗ Error during auto-split: {e}")
        return []


def ingest_single_file(file_path: Path) -> bool:
    """Ingest a single file into ChromaDB."""
    print(f"Processing: {file_path}")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False
    
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check file size
        file_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")
        
        # Count tokens
        total_tokens = count_tokens(content)
        print(f"Total tokens: {total_tokens}")
        
        # Split into chunks if needed
        if total_tokens > MAX_CHUNK_TOKENS:
            print(f"Splitting into chunks (max {MAX_CHUNK_TOKENS} tokens each, {CHUNK_OVERLAP} token overlap)...")
            chunks = split_text_semantic(content, MAX_CHUNK_TOKENS, CHUNK_OVERLAP)
            print(f"Created {len(chunks)} chunks with {CHUNK_OVERLAP}-token overlap")
        else:
            chunks = [content]
        
        # Initialize clients
        openai_client = get_openai_client()
        collection = get_collection()
        
        # Ingest chunks
        success = ingest_file_chunks(file_path, chunks, openai_client, collection)
        
        # Cleanup
        del content, chunks, openai_client, collection
        gc.collect()
        
        return success
        
    except MemoryError:
        print("Memory error - file too large, attempting auto-split...")
        segments = auto_split_file(file_path)
        if segments:
            # Add segments to queue
            queue = load_queue()
            for segment in segments:
                segment_str = str(segment)
                if segment_str not in queue['pending']:
                    queue['pending'].append(segment_str)
            save_queue(queue)
            print(f"✓ Added {len(segments)} segments to queue")
        return False
    except Exception as e:
        print(f"Error processing file: {e}")
        traceback.print_exc()
        # Try auto-split on any error
        if "too large" in str(e).lower() or "memory" in str(e).lower():
            segments = auto_split_file(file_path)
            if segments:
                queue = load_queue()
                for segment in segments:
                    segment_str = str(segment)
                    if segment_str not in queue['pending']:
                        queue['pending'].append(segment_str)
                save_queue(queue)
        return False


def main():
    """Main execution: process exactly one file."""
    print("=" * 70)
    print("SINGLE-FILE INGESTION PIPELINE")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Queue file: {QUEUE_FILE}")
    print()
    
    # Load queue
    queue = load_queue()
    
    # Get next file
    file_path = get_next_file(queue)
    
    if not file_path:
        print("No pending files in queue.")
        print(f"Completed: {len(queue.get('completed', []))}")
        print(f"Failed: {len(queue.get('failed', []))}")
        return 0
    
    # Process file
    print(f"Processing file: {file_path}")
    success = ingest_single_file(file_path)
    
    # Update queue and checkpoint
    mark_file_complete(queue, file_path, success)
    
    checkpoint = load_checkpoint()
    if success:
        checkpoint["processed_files"][str(file_path)] = {
            "timestamp": time.time(),
            "status": "completed"
        }
    else:
        checkpoint["failed_files"][str(file_path)] = {
            "timestamp": time.time(),
            "status": "failed"
        }
    save_checkpoint(checkpoint)
    
    if success:
        print(f"✓ Successfully ingested: {file_path}")
        return 0
    else:
        print(f"✗ Failed to ingest: {file_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

