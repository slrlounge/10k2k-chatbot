#!/usr/bin/env python3
"""
Ultra-Minimal Ingestion - Most aggressive memory optimizations
Processes files in tiny chunks with maximum delays and cleanup
"""

import os
import sys
import gc
import time
import traceback
import socket
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

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))  # Ultra-small chunks
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '50'))
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))

# Set socket timeout to prevent hanging connections
socket.setdefaulttimeout(30)  # 30 second timeout

logger = setup_logger('ingest_ultra_minimal')


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
    """Process file with ultra-minimal memory footprint."""
    file_size_mb = transcript_file.stat().st_size / (1024 * 1024)
    file_str = str(transcript_file)
    
    logger.info(f"Processing: {transcript_file.name} ({file_size_mb:.2f}MB) [ULTRA-MINIMAL MODE]")
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"Skipping {transcript_file.name}: too large")
        mark_processed(file_str, success=False)
        return 1
    
    client = None
    collection = None
    openai_client = None
    
    try:
        # Import ChromaDB utilities with retry logic
        try:
            from ingestion.utils_chromadb import (
                get_chroma_client_with_retry,
                get_collection_with_retry,
                add_chunks_with_retry,
                get_collection_count_with_retry
            )
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from ingestion.utils_chromadb import (
                get_chroma_client_with_retry,
                get_collection_with_retry,
                add_chunks_with_retry,
                get_collection_count_with_retry
            )
        
        # Connect to ChromaDB server with retry logic
        logger.info(f"Connecting to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
        try:
            client = get_chroma_client_with_retry(host=CHROMA_HOST, port=CHROMA_PORT)
            logger.info("✓ Connected to remote ChromaDB")
        except Exception as e:
            logger.error(f"Failed to create ChromaDB client: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Get or create collection with retry logic
        logger.info(f"Getting/creating collection: {COLLECTION_NAME}")
        try:
            collection = get_collection_with_retry(client, COLLECTION_NAME)
            initial_count = get_collection_count_with_retry(collection)
            logger.info(f"✓ Collection '{COLLECTION_NAME}' ready ({initial_count:,} documents)")
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Initialize OpenAI client with error handling
        logger.info("Initializing OpenAI client...")
        try:
            api_key = get_openai_api_key()
            openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Aggressive GC after initialization
        for _ in range(3):
            gc.collect()
        time.sleep(0.5)  # Longer delay to stabilize
        
        # Load file content with error handling
        logger.info(f"Reading file: {transcript_file}")
        try:
            content = ""
            with open(transcript_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"File read successfully: {len(content)} characters")
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            logger.error(traceback.format_exc())
            raise
        
        del f
        for _ in range(2):
            gc.collect()
        
        # Chunk text
        text_chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        logger.info(f"Created {len(text_chunks)} chunks (size={CHUNK_SIZE} tokens)")
        
        # Clear content after chunking
        del content
        for _ in range(3):
            gc.collect()
        time.sleep(0.3)
        
        # Process chunks ONE AT A TIME with maximum delays
        total_added = 0
        
        for i, chunk_text_content in enumerate(text_chunks):
            try:
                # Generate embedding
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
                
                chunk_id = f"{transcript_file.stem}_{i}"
                
                # Add to ChromaDB with retry and duplicate checking
                added = add_chunks_with_retry(
                    collection=collection,
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk_text_content.strip()],
                    metadatas=[metadata],
                    batch_size=1
                )
                
                if added > 0:
                    total_added += 1
                
                # ULTRA-AGGRESSIVE cleanup after each chunk
                del embedding
                del response
                del chunk_text_content
                del metadata
                
                # Multiple GC passes
                for _ in range(3):
                    gc.collect()
                
                # Longer delay after EVERY chunk
                time.sleep(0.3)
                
                # Extra delay every 3 chunks
                if (i + 1) % 3 == 0:
                    time.sleep(0.5)
                    for _ in range(2):
                        gc.collect()
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i}: {str(e)[:80]}")
                for _ in range(3):
                    gc.collect()
                time.sleep(0.5)
                continue
        
        final_count = get_collection_count_with_retry(collection)
        logger.info(f"✓ Successfully processed {transcript_file.name}: {total_added} chunks added")
        logger.info(f"✓ Collection '{COLLECTION_NAME}' now contains {final_count:,} documents after insertion")
        logger.info("✓ No local ChromaDB directories remain - all data in remote ChromaDB")
        mark_processed(file_str, success=True)
        return 0
        
    except MemoryError as e:
        logger.error(f"Memory error processing {transcript_file.name}: {e}")
        logger.error(traceback.format_exc())
        mark_processed(file_str, success=False)
        return 1
    except Exception as e:
        logger.error(f"Error processing {transcript_file.name}: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(traceback.format_exc())
        mark_processed(file_str, success=False)
        return 1
    finally:
        # Maximum cleanup
        if collection:
            del collection
        if client:
            del client
        if openai_client:
            del openai_client
        for _ in range(5):
            gc.collect()
        time.sleep(0.2)


def main():
    # Log startup immediately
    logger.info("=" * 60)
    logger.info("ULTRA-MINIMAL INGESTION STARTING")
    logger.info("=" * 60)
    
    if len(sys.argv) < 2:
        logger.error("Usage: python ingest_single_transcript_ultra_minimal.py <transcript_file_path>")
        sys.exit(1)
    
    transcript_path = Path(sys.argv[1])
    logger.info(f"File argument: {transcript_path}")
    logger.info(f"ChromaDB Host: {CHROMA_HOST}")
    logger.info(f"ChromaDB Port: {CHROMA_PORT}")
    logger.info(f"Collection Name: {COLLECTION_NAME}")
    logger.info(f"Chunk Size: {CHUNK_SIZE} tokens")
    
    if not transcript_path.exists():
        logger.error(f"File not found: {transcript_path}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Absolute path: {transcript_path.absolute()}")
        sys.exit(1)
    
    if not transcript_path.is_file():
        logger.error(f"Not a file: {transcript_path}")
        sys.exit(1)
    
    file_str = str(transcript_path)
    if is_processed(file_str):
        logger.info(f"Already processed: {transcript_path.name}")
        return 0
    
    logger.info("=" * 60)
    logger.info("Starting file processing...")
    logger.info("=" * 60)
    
    try:
        result = process_transcript_file(transcript_path)
        logger.info(f"File processing completed with exit code: {result}")
        return result
    except Exception as e:
        logger.error(f"Fatal error in main(): {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)

