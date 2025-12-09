#!/usr/bin/env python3
"""
Single Transcript Ingestion Script
Processes ONE transcript file specified as command-line argument.
Designed for Docker, uses HttpClient to connect to ChromaDB server.
Each run uses a fresh Python process - memory is fully released after completion.
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
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import is_processed, mark_processed

# Load environment variables
load_dotenv()

# Configuration from environment
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/transcripts'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '4000'))  # Increased to reduce total chunks
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '400'))  # Increased proportionally
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))

# Initialize logger
logger = setup_logger('ingest_single')


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables!")
        sys.exit(1)
    return api_key


def load_transcript(file_path: Path):
    """Load transcript file and return Document objects with metadata."""
    try:
        loader = TextLoader(str(file_path), encoding='utf-8')
        docs = loader.load()
        
        for doc in docs:
            doc.metadata['filename'] = file_path.name
            doc.metadata['type'] = 'transcript'
            doc.metadata['source'] = str(file_path)
            
            # Add relative path if possible
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
    """Split text into chunks using tiktoken tokenizer."""
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
    """
    Process a single transcript file.
    Returns 0 on success, 1 on failure.
    """
    file_size_mb = transcript_file.stat().st_size / (1024 * 1024)
    file_str = str(transcript_file)
    
    logger.info(f"Processing: {transcript_file.name} ({file_size_mb:.2f}MB)")
    
    # Check file size
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"Skipping {transcript_file.name}: file too large ({file_size_mb:.2f}MB > {MAX_FILE_SIZE_MB}MB)")
        mark_processed(file_str, success=False)
        return 1
    
    try:
        # Connect to ChromaDB server (Docker)
        logger.debug(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Initialize embeddings AFTER client connection
        api_key = get_openai_api_key()
        embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model="text-embedding-3-small"  # Smaller model uses less memory
        )
        
        # Create vectorstore - NO persist_directory (incompatible with HttpClient)
        # Use minimal settings to reduce memory footprint
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        
        # Force garbage collection after initialization
        gc.collect()
        
        # Brief pause to allow memory to stabilize
        time.sleep(0.2)
        
        # Load transcript
        documents = load_transcript(transcript_file)
        if not documents:
            logger.error(f"Failed to load transcript: {transcript_file}")
            mark_processed(file_str, success=False)
            return 1
        
        # Process chunks ONE AT A TIME with immediate cleanup to minimize memory
        total_chunks = 0
        chunk_count = 0
        
        for doc in documents:
            text_chunks = chunk_text(doc.page_content, CHUNK_SIZE, CHUNK_OVERLAP)
            
            for chunk_content in text_chunks:
                chunk_count += 1
                
                # Create document for this chunk only
                chunk_doc = Document(
                    page_content=chunk_content.strip(),
                    metadata=doc.metadata.copy()
                )
                
                # Process ONE chunk at a time with immediate cleanup
                try:
                    # Add single chunk with retry logic
                    max_retries = 2
                    success = False
                    for attempt in range(max_retries):
                        try:
                            # Add single document - minimal memory footprint
                            vectorstore.add_documents([chunk_doc])
                            total_chunks += 1
                            success = True
                            break
                        except Exception as e:
                            if attempt < max_retries - 1:
                                logger.debug(f"Retry {attempt + 1}/{max_retries} for chunk {chunk_count}")
                                time.sleep(0.5)
                                gc.collect()
                                continue
                            else:
                                raise
                    
                    # IMMEDIATE cleanup after each chunk
                    del chunk_doc
                    gc.collect()
                    
                    # Small delay only every 5 chunks to reduce overhead
                    if chunk_count % 5 == 0:
                        time.sleep(0.05)
                    
                except Exception as e:
                    logger.warning(f"Failed to add chunk {chunk_count}: {str(e)[:80]}")
                    del chunk_doc
                    gc.collect()
                    continue
        
        logger.info(f"Successfully processed {transcript_file.name}: {total_chunks} chunks added")
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
        # Aggressive cleanup - release all resources
        try:
            if 'vectorstore' in locals():
                del vectorstore
            if 'embeddings' in locals():
                del embeddings
            if 'client' in locals():
                del client
            if 'documents' in locals():
                del documents
        except:
            pass
        
        # Multiple GC passes to ensure cleanup
        for _ in range(3):
            gc.collect()
        
        # Brief pause to allow OS to reclaim memory
        time.sleep(0.1)


def main():
    """Main function - accepts file path as command-line argument."""
    if len(sys.argv) < 2:
        logger.error("Usage: python ingest_single_transcript.py <transcript_file_path>")
        logger.error("Example: python ingest_single_transcript.py '/path/to/transcript.txt'")
        sys.exit(1)
    
    transcript_path = Path(sys.argv[1])
    
    if not transcript_path.exists():
        logger.error(f"File not found: {transcript_path}")
        sys.exit(1)
    
    if not transcript_path.is_file():
        logger.error(f"Not a file: {transcript_path}")
        sys.exit(1)
    
    # Check if already processed
    file_str = str(transcript_path)
    if is_processed(file_str):
        logger.info(f"Already processed: {transcript_path.name}")
        return 0
    
    # Process the file
    result = process_transcript_file(transcript_path)
    
    return result


if __name__ == '__main__':
    sys.exit(main() or 0)

