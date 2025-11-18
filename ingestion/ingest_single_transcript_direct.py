#!/usr/bin/env python3
"""
Direct API Ingestion - Bypasses LangChain to minimize memory usage
Uses OpenAI API directly for embeddings and ChromaDB HTTP API directly
"""

import os
import sys
import gc
import time
import json
from pathlib import Path
from dotenv import load_dotenv
import tiktoken
import requests
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
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '2000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))

logger = setup_logger('ingest_direct')


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


def ensure_collection_exists(chroma_url: str, collection_name: str) -> bool:
    """Ensure ChromaDB collection exists, create if not."""
    try:
        # Use v2 API - check if collection exists
        response = requests.get(f"{chroma_url}/api/v2/collections/{collection_name}", timeout=5)
        if response.status_code == 200:
            return True
        
        # Create collection if it doesn't exist (v2 API)
        if response.status_code == 404:
            create_data = {
                "name": collection_name,
                "metadata": {}
            }
            response = requests.post(
                f"{chroma_url}/api/v2/collections",
                json=create_data,
                timeout=10
            )
            if response.status_code in [200, 201]:
                logger.info(f"Created collection: {collection_name}")
                return True
        
        logger.error(f"Failed to ensure collection exists: {response.status_code} - {response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"Error ensuring collection: {e}")
        return False


def add_to_chroma_direct(chroma_url: str, collection_name: str, texts: list, embeddings: list, metadatas: list, ids: list):
    """Add documents directly to ChromaDB via HTTP API (v2)."""
    try:
        add_data = {
            "ids": ids,
            "embeddings": embeddings,
            "documents": texts,
            "metadatas": metadatas
        }
        
        # Use v2 API endpoint
        response = requests.post(
            f"{chroma_url}/api/v2/collections/{collection_name}/add",
            json=add_data,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"ChromaDB API error: {response.status_code} - {response.text[:200]}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to add to ChromaDB: {e}")
        raise


def process_transcript_file(transcript_file: Path) -> int:
    """Process file using direct API calls - minimal memory footprint."""
    file_size_mb = transcript_file.stat().st_size / (1024 * 1024)
    file_str = str(transcript_file)
    
    logger.info(f"Processing: {transcript_file.name} ({file_size_mb:.2f}MB)")
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"Skipping {transcript_file.name}: too large")
        mark_processed(file_str, success=False)
        return 1
    
    chroma_url = f"http://{CHROMA_HOST}:{CHROMA_PORT}"
    openai_client = None
    
    try:
        # Initialize OpenAI client (lightweight)
        api_key = get_openai_api_key()
        openai_client = OpenAI(api_key=api_key)
        
        # Ensure collection exists
        if not ensure_collection_exists(chroma_url, COLLECTION_NAME):
            logger.error("Failed to ensure collection exists")
            mark_processed(file_str, success=False)
            return 1
        
        # Load file content
        with open(transcript_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Chunk text
        text_chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        logger.info(f"Created {len(text_chunks)} chunks")
        
        # Process chunks in very small batches (1-2 at a time)
        total_added = 0
        batch_size = 1  # Process one chunk at a time
        
        for i, chunk_text_content in enumerate(text_chunks):
            try:
                # Generate embedding directly via OpenAI API
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
                    "chunk_index": i
                }
                
                # Add relative path if possible
                try:
                    if TRANSCRIPTS_DIR.exists():
                        rel_path = transcript_file.relative_to(TRANSCRIPTS_DIR)
                        metadata["relative_path"] = str(rel_path.parent) if rel_path.parent != Path('.') else ''
                except ValueError:
                    metadata["relative_path"] = ''
                
                # Generate unique ID
                chunk_id = f"{transcript_file.stem}_{i}"
                
                # Add to ChromaDB directly
                add_to_chroma_direct(
                    chroma_url=chroma_url,
                    collection_name=COLLECTION_NAME,
                    texts=[chunk_text_content.strip()],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[chunk_id]
                )
                
                total_added += 1
                
                # Immediate cleanup
                del embedding
                del response
                gc.collect()
                
                # Small delay every 3 chunks
                if (i + 1) % 3 == 0:
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
        # Cleanup
        if openai_client:
            del openai_client
        for _ in range(3):
            gc.collect()
        time.sleep(0.1)


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python ingest_single_transcript_direct.py <transcript_file_path>")
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

