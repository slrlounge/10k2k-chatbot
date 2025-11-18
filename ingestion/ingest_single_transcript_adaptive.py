#!/usr/bin/env python3
"""
Adaptive Single Transcript Ingestion Script
Automatically reduces chunk size and retries if files fail due to memory issues.
"""

import os
import sys
import gc
import time
from pathlib import Path
from dotenv import load_dotenv
import tiktoken

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
import chromadb

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
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))

logger = setup_logger('ingest_single_adaptive')


def get_openai_api_key() -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found!")
        sys.exit(1)
    return api_key


def load_transcript(file_path: Path):
    try:
        loader = TextLoader(str(file_path), encoding='utf-8')
        docs = loader.load()
        for doc in docs:
            doc.metadata['filename'] = file_path.name
            doc.metadata['type'] = 'transcript'
            doc.metadata['source'] = str(file_path)
            try:
                if TRANSCRIPTS_DIR.exists():
                    rel_path = file_path.relative_to(TRANSCRIPTS_DIR)
                    doc.metadata['relative_path'] = str(rel_path.parent) if rel_path.parent != Path('.') else ''
                else:
                    doc.metadata['relative_path'] = ''
            except ValueError:
                doc.metadata['relative_path'] = ''
        return docs
    except Exception as e:
        logger.error(f"Failed to load transcript {file_path}: {e}")
        return []


def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
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


def process_with_chunk_size(transcript_file: Path, chunk_size: int, chunk_overlap: int) -> tuple:
    """Process file with specific chunk size. Returns (success, chunks_added)."""
    client = None
    embeddings = None
    vectorstore = None
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        api_key = get_openai_api_key()
        embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model="text-embedding-3-small"
        )
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        gc.collect()
        
        documents = load_transcript(transcript_file)
        if not documents:
            return False, 0
        
        total_chunks = 0
        for doc in documents:
            text_chunks = chunk_text(doc.page_content, chunk_size, chunk_overlap)
            
            for chunk_content in text_chunks:
                chunk_doc = Document(
                    page_content=chunk_content.strip(),
                    metadata=doc.metadata.copy()
                )
                
                try:
                    vectorstore.add_documents([chunk_doc])
                    total_chunks += 1
                    del chunk_doc
                    gc.collect()
                    # Small delay every 3 chunks
                    if total_chunks % 3 == 0:
                        time.sleep(0.05)
                except Exception as e:
                    logger.warning(f"Failed chunk: {str(e)[:50]}")
                    del chunk_doc
                    gc.collect()
                    continue
        
        # Cleanup
        del vectorstore
        del embeddings
        del client
        for _ in range(3):
            gc.collect()
        
        return True, total_chunks
        
    except Exception as e:
        logger.error(f"Error with chunk_size={chunk_size}: {e}")
        try:
            if 'vectorstore' in locals():
                del vectorstore
            if 'embeddings' in locals():
                del embeddings
            if 'client' in locals():
                del client
        except:
            pass
        gc.collect()
        return False, 0


def process_transcript_file(transcript_file: Path) -> int:
    """Process file with adaptive chunk sizing - automatically reduces if needed."""
    file_size_mb = transcript_file.stat().st_size / (1024 * 1024)
    file_str = str(transcript_file)
    
    logger.info(f"Processing: {transcript_file.name} ({file_size_mb:.2f}MB)")
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"Skipping {transcript_file.name}: too large")
        mark_processed(file_str, success=False)
        return 1
    
    # Try progressively smaller chunk sizes if files fail
    chunk_configs = [
        (4000, 400),   # Try large chunks first (fewer API calls)
        (2000, 200),   # Medium chunks
        (1000, 100),   # Small chunks
        (500, 50),     # Very small chunks (more API calls but less memory per call)
    ]
    
    for chunk_size, chunk_overlap in chunk_configs:
        logger.info(f"Attempting with chunk_size={chunk_size}, overlap={chunk_overlap}")
        success, chunks_added = process_with_chunk_size(transcript_file, chunk_size, chunk_overlap)
        
        if success and chunks_added > 0:
            logger.info(f"✓ Successfully processed {transcript_file.name}: {chunks_added} chunks (chunk_size={chunk_size})")
            mark_processed(file_str, success=True)
            return 0
        elif success:
            logger.warning(f"Processed but no chunks added - trying smaller chunks")
            continue
        else:
            logger.warning(f"Failed with chunk_size={chunk_size} - trying smaller chunks")
            time.sleep(1)  # Brief pause before retry
            continue
    
    # All attempts failed
    logger.error(f"✗ All chunk size attempts failed for {transcript_file.name}")
    mark_processed(file_str, success=False)
    return 1


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python ingest_single_transcript_adaptive.py <transcript_file_path>")
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

