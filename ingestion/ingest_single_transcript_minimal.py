#!/usr/bin/env python3
"""
Minimal Memory Ingestion - Uses ChromaDB Python client with ultra-aggressive memory management
Bypasses LangChain embeddings wrapper to reduce memory overhead
"""

import os
import sys
import gc
import time
from pathlib import Path
from dotenv import load_dotenv
import tiktoken
import chromadb
from openai import OpenAI

try:
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import is_processed, mark_processed
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import is_processed, mark_processed

load_dotenv()

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/transcripts'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))  # Reduced to 1000 tokens
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))  # Reduced overlap
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))

logger = setup_logger('ingest_minimal')


def get_openai_api_key() -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found!")
        sys.exit(1)
    return api_key


def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """Split text into chunks using tiktoken."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(encoding.decode(tokens[start:end]))
        start = end - overlap
        if start >= len(tokens):
            break
    
    return chunks


def process_transcript_file(transcript_file: Path) -> int:
    """Process file with minimal memory footprint."""
    file_size_mb = transcript_file.stat().st_size / (1024 * 1024)
    file_str = str(transcript_file)
    
    logger.info(f"Processing: {transcript_file.name} ({file_size_mb:.2f}MB)")
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"Skipping {transcript_file.name}: too large")
        mark_processed(file_str, success=False)
        return 1
    
    client = None
    collection = None
    openai_client = None
    
    try:
        # Connect to ChromaDB server
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Get or create collection
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except:
            collection = client.create_collection(name=COLLECTION_NAME)
        
        # Initialize OpenAI client (lightweight)
        api_key = get_openai_api_key()
        openai_client = OpenAI(api_key=api_key)
        
        # Force GC after initialization
        gc.collect()
        time.sleep(0.2)  # Allow memory to stabilize
        
        # Load file content - read in chunks to avoid loading entire file
        content = ""
        with open(transcript_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clear file handle immediately
        del f
        gc.collect()
        
        # Chunk text
        text_chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        logger.info(f"Created {len(text_chunks)} chunks")
        
        # Clear content after chunking
        del content
        gc.collect()
        
        # Process chunks ONE AT A TIME
        total_added = 0
        
        for i, chunk_text_content in enumerate(text_chunks):
            try:
                # Generate embedding directly
                response = openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk_text_content.strip()
                )
                embedding = response.data[0].embedding
                
                # Prepare metadata
                metadata = {
                    "filename": transcript_file.name,
                    "type": "transcript",
                    "source": str(transcript_file),
                    "chunk_index": str(i)
                }
                
                try:
                    if TRANSCRIPTS_DIR.exists():
                        rel_path = transcript_file.relative_to(TRANSCRIPTS_DIR)
                        metadata["relative_path"] = str(rel_path.parent) if rel_path.parent != Path('.') else ''
                except ValueError:
                    metadata["relative_path"] = ''
                
                # Generate unique ID
                chunk_id = f"{transcript_file.stem}_{i}"
                
                # Add to ChromaDB - ONE chunk at a time
                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk_text_content.strip()],
                    metadatas=[metadata]
                )
                
                total_added += 1
                
                # IMMEDIATE cleanup - more aggressive
                del embedding
                del response
                del chunk_text_content
                gc.collect()
                gc.collect()  # Double GC pass
                
                # Delay after EVERY chunk to allow memory release
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i}: {str(e)[:80]}")
                gc.collect()
                continue
        
        logger.info(f"Successfully processed {transcript_file.name}: {total_added} chunks added")
        mark_processed(file_str, success=True)
        return 0
        
    except MemoryError:
        logger.error(f"Memory error processing {transcript_file.name}")
        mark_processed(file_str, success=False)
        return 1
    except Exception as e:
        logger.error(f"Error processing {transcript_file.name}: {e}")
        mark_processed(file_str, success=False)
        return 1
    finally:
        # Aggressive cleanup
        if collection:
            del collection
        if client:
            del client
        if openai_client:
            del openai_client
        for _ in range(3):
            gc.collect()
        time.sleep(0.1)


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python ingest_single_transcript_minimal.py <transcript_file_path>")
        sys.exit(1)
    
    transcript_path = Path(sys.argv[1])
    
    if not transcript_path.exists():
        logger.error(f"File not found: {transcript_path}")
        sys.exit(1)
    
    if not transcript_path.is_file():
        logger.error(f"Not a file: {transcript_path}")
        sys.exit(1)
    
    file_str = str(transcript_path)
    if is_processed(file_str):
        logger.info(f"Already processed: {transcript_path.name}")
        return 0
    
    result = process_transcript_file(transcript_path)
    return result


if __name__ == '__main__':
    sys.exit(main() or 0)

