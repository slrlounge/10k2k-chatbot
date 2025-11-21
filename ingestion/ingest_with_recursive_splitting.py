#!/usr/bin/env python3
"""
Recursive File Splitting & Cloud Ingestion
Automatically splits large files that fail ingestion and retries until all segments succeed.
"""

import os
import sys
import re
import subprocess
import time
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv
import chromadb

try:
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import get_processed, mark_processed, is_processed
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import get_processed, mark_processed, is_processed

load_dotenv()

# Configuration
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
INGEST_SCRIPT = Path(os.getenv('INGEST_SCRIPT_ULTRA_MINIMAL', '/app/ingestion/ingest_single_transcript_ultra_minimal.py'))
PYTHON_CMD = os.getenv('PYTHON_CMD', 'python3')
MAX_INITIAL_SIZE_MB = float(os.getenv('MAX_INITIAL_SIZE_MB', '10.0'))
MIN_SEGMENT_SIZE_KB = float(os.getenv('MIN_SEGMENT_SIZE_KB', '50.0'))  # Minimum 50KB per segment
MAX_RECURSION_DEPTH = int(os.getenv('MAX_RECURSION_DEPTH', '5'))  # Max 5 levels of splitting
RETRY_DELAY_SECONDS = float(os.getenv('RETRY_DELAY_SECONDS', '2.0'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

logger = setup_logger('ingest_recursive_split')

# Track statistics
stats = {
    'files_processed': 0,
    'files_split': 0,
    'segments_created': 0,
    'recursion_levels': {},
    'files_failed': []
}


def split_at_semantic_boundaries(content: str, target_size_bytes: int) -> List[str]:
    """
    Split text at semantic boundaries (paragraphs, sentences, line breaks).
    Never splits words or mid-sentence.
    
    Args:
        content: Text content to split
        target_size_bytes: Target size for each segment in bytes
    
    Returns:
        List of text segments split at semantic boundaries
    """
    segments = []
    
    # First, try splitting by double newlines (paragraphs)
    paragraphs = content.split('\n\n')
    
    current_segment = ""
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para.encode('utf-8'))
        
        # If single paragraph exceeds target, split by single newlines
        if para_size > target_size_bytes:
            lines = para.split('\n')
            for line in lines:
                line_size = len(line.encode('utf-8'))
                
                # If single line exceeds target, split by sentences
                if line_size > target_size_bytes:
                    sentences = re.split(r'(?<=[.!?])\s+', line)
                    for sentence in sentences:
                        sent_size = len(sentence.encode('utf-8'))
                        
                        # If single sentence exceeds target, split by commas/clauses
                        if sent_size > target_size_bytes:
                            clauses = re.split(r'(?<=[,;:])\s+', sentence)
                            for clause in clauses:
                                clause_size = len(clause.encode('utf-8'))
                                
                                if current_size + clause_size > target_size_bytes and current_segment:
                                    segments.append(current_segment.strip())
                                    current_segment = clause
                                    current_size = clause_size
                                else:
                                    current_segment += (" " + clause if current_segment else clause)
                                    current_size += clause_size
                        else:
                            if current_size + sent_size > target_size_bytes and current_segment:
                                segments.append(current_segment.strip())
                                current_segment = sentence
                                current_size = sent_size
                            else:
                                current_segment += (" " + sentence if current_segment else sentence)
                                current_size += sent_size
                else:
                    if current_size + line_size > target_size_bytes and current_segment:
                        segments.append(current_segment.strip())
                        current_segment = line
                        current_size = line_size
                    else:
                        current_segment += ("\n" + line if current_segment else line)
                        current_size += line_size
        else:
            if current_size + para_size > target_size_bytes and current_segment:
                segments.append(current_segment.strip())
                current_segment = para
                current_size = para_size
            else:
                current_segment += ("\n\n" + para if current_segment else para)
                current_size += para_size
    
    # Add remaining segment
    if current_segment.strip():
        segments.append(current_segment.strip())
    
    return segments


def create_segment_file(original_file: Path, segment_num: int, content: str, temp_dir: Path) -> Path:
    """
    Create a segment file with proper naming convention.
    
    Args:
        original_file: Original file path
        segment_num: Segment number (1-indexed)
        content: Content for this segment
        temp_dir: Temporary directory for segments
    
    Returns:
        Path to created segment file
    """
    # Get base name without extension
    base_name = original_file.stem
    extension = original_file.suffix
    
    # Create segment filename: originalname_01.txt, originalname_02.txt, etc.
    segment_name = f"{base_name}_{segment_num:02d}{extension}"
    segment_path = temp_dir / segment_name
    
    # Write segment content
    with open(segment_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return segment_path


def verify_in_chromadb(segment_path: Path) -> bool:
    """
    Verify that a segment is actually stored in ChromaDB.
    
    Args:
        segment_path: Path to segment file
    
    Returns:
        True if segment is found in ChromaDB, False otherwise
    """
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(name=COLLECTION_NAME)
        
        # Check if any documents with this filename exist
        segment_name = segment_path.name
        results = collection.get(
            where={"filename": segment_name},
            limit=1
        )
        
        return len(results.get('ids', [])) > 0
    except Exception as e:
        logger.warning(f"Could not verify segment in ChromaDB: {e}")
        return False


def ingest_file_segment(segment_path: Path, retry_count: int = 0) -> bool:
    """
    Ingest a single file segment using the ultra-minimal script.
    
    Args:
        segment_path: Path to segment file
        retry_count: Current retry attempt
    
    Returns:
        True if successful, False otherwise
    """
    if retry_count >= MAX_RETRIES:
        logger.error(f"Max retries ({MAX_RETRIES}) exceeded for {segment_path.name}")
        return False
    
    try:
        logger.info(f"Ingesting segment: {segment_path.name} (attempt {retry_count + 1}/{MAX_RETRIES})")
        
        result = subprocess.run(
            [PYTHON_CMD, str(INGEST_SCRIPT), str(segment_path)],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        if result.returncode == 0:
            # Verify segment is actually in ChromaDB
            if verify_in_chromadb(segment_path):
                logger.info(f"✓ Successfully ingested and verified: {segment_path.name}")
                mark_processed(str(segment_path), success=True)
                return True
            else:
                logger.warning(f"⚠️  Ingestion reported success but segment not found in ChromaDB: {segment_path.name}")
                # Retry
                time.sleep(RETRY_DELAY_SECONDS * (retry_count + 1))
                return ingest_file_segment(segment_path, retry_count + 1)
        else:
            logger.warning(f"⚠️  Ingestion failed (exit {result.returncode}): {segment_path.name}")
            if result.stderr:
                logger.warning(f"Error: {result.stderr[:500]}")
            
            # Retry with exponential backoff
            time.sleep(RETRY_DELAY_SECONDS * (2 ** retry_count))
            return ingest_file_segment(segment_path, retry_count + 1)
            
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️  Timeout ingesting: {segment_path.name}")
        time.sleep(RETRY_DELAY_SECONDS * (2 ** retry_count))
        return ingest_file_segment(segment_path, retry_count + 1)
    except Exception as e:
        logger.error(f"✗ Error ingesting {segment_path.name}: {e}")
        return False


def process_file_recursive(file_path: Path, recursion_level: int = 0, temp_dir: Optional[Path] = None) -> bool:
    """
    Recursively process a file, splitting if necessary until all segments succeed.
    
    Args:
        file_path: Path to file to process
        recursion_level: Current recursion depth
        temp_dir: Temporary directory for segments
    
    Returns:
        True if all segments succeeded, False otherwise
    """
    if recursion_level >= MAX_RECURSION_DEPTH:
        logger.error(f"Max recursion depth ({MAX_RECURSION_DEPTH}) reached for {file_path.name}")
        stats['files_failed'].append(str(file_path))
        return False
    
    # Track recursion levels
    if recursion_level not in stats['recursion_levels']:
        stats['recursion_levels'][recursion_level] = 0
    stats['recursion_levels'][recursion_level] += 1
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    logger.info(f"{'  ' * recursion_level}Processing: {file_path.name} ({file_size_mb:.2f}MB, level {recursion_level})")
    
    # Check if already processed
    if is_processed(str(file_path)):
        logger.info(f"{'  ' * recursion_level}✓ Already processed: {file_path.name}")
        return True
    
    # Try ingesting as-is first
    if file_size_mb <= MAX_INITIAL_SIZE_MB:
        logger.info(f"{'  ' * recursion_level}Attempting to ingest as-is...")
        if ingest_file_segment(file_path):
            logger.info(f"{'  ' * recursion_level}✓ Successfully ingested: {file_path.name}")
            stats['files_processed'] += 1
            return True
        else:
            logger.warning(f"{'  ' * recursion_level}⚠️  Ingestion failed, will split: {file_path.name}")
    
    # File is too large or ingestion failed - need to split
    logger.info(f"{'  ' * recursion_level}Splitting file: {file_path.name}")
    
    # Create temp directory for segments
    if temp_dir is None:
        temp_dir = file_path.parent / f".segments_{file_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"✗ Failed to read file {file_path.name}: {e}")
        stats['files_failed'].append(str(file_path))
        return False
    
    # Calculate target segment size
    # Start with half the file size, but ensure minimum size
    target_size_bytes = max(
        int(len(content.encode('utf-8')) / 2),
        int(MIN_SEGMENT_SIZE_KB * 1024)
    )
    
    # Split at semantic boundaries
    segments = split_at_semantic_boundaries(content, target_size_bytes)
    logger.info(f"{'  ' * recursion_level}Split into {len(segments)} segments")
    
    if len(segments) == 1:
        # Couldn't split further - try ingesting as-is
        logger.warning(f"{'  ' * recursion_level}Could not split further, attempting ingestion...")
        if ingest_file_segment(file_path):
            logger.info(f"{'  ' * recursion_level}✓ Successfully ingested unsplit: {file_path.name}")
            stats['files_processed'] += 1
            return True
        else:
            logger.error(f"{'  ' * recursion_level}✗ Failed to ingest unsplit file: {file_path.name}")
            stats['files_failed'].append(str(file_path))
            return False
    
    # Create segment files
    segment_files = []
    for i, segment_content in enumerate(segments, 1):
        segment_file = create_segment_file(file_path, i, segment_content, temp_dir)
        segment_files.append(segment_file)
        stats['segments_created'] += 1
    
    # Process each segment recursively
    all_succeeded = True
    for segment_file in segment_files:
        if not process_file_recursive(segment_file, recursion_level + 1, temp_dir):
            all_succeeded = False
    
    # Cleanup temp directory if all segments succeeded
    if all_succeeded:
        logger.info(f"{'  ' * recursion_level}✓ All segments succeeded for: {file_path.name}")
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Could not cleanup temp directory {temp_dir}: {e}")
        
        # Mark original file as processed
        mark_processed(str(file_path), success=True)
        stats['files_split'] += 1
        return True
    else:
        logger.error(f"{'  ' * recursion_level}✗ Some segments failed for: {file_path.name}")
        stats['files_failed'].append(str(file_path))
        return False


def identify_failed_files() -> List[Path]:
    """
    Identify files that failed to upload by comparing all files with processed files.
    
    Returns:
        List of Path objects for failed files
    """
    logger.info("Identifying failed files...")
    
    # Find all transcript files
    all_files = []
    if TRANSCRIPTS_DIR.exists():
        all_files = list(TRANSCRIPTS_DIR.rglob('*.txt'))
    
    logger.info(f"Found {len(all_files)} total transcript files")
    
    # Get processed files from checkpoint
    processed = get_processed()
    logger.info(f"Found {len(processed)} processed files in checkpoint")
    
    # Find failed files (not in processed set)
    failed_files = []
    for file_path in all_files:
        file_str = str(file_path)
        if file_str not in processed:
            failed_files.append(file_path)
    
    logger.info(f"Identified {len(failed_files)} failed/unprocessed files")
    
    return failed_files


def main():
    """Main orchestration function."""
    logger.info("=" * 70)
    logger.info("RECURSIVE FILE SPLITTING & CLOUD INGESTION")
    logger.info("=" * 70)
    
    # Identify failed files
    failed_files = identify_failed_files()
    
    if not failed_files:
        logger.info("✅ No failed files found. All files have been processed!")
        return 0
    
    logger.info(f"\nProcessing {len(failed_files)} failed files...")
    logger.info("=" * 70)
    
    # Process each failed file recursively
    for i, file_path in enumerate(failed_files, 1):
        logger.info(f"\n[{i}/{len(failed_files)}] Processing: {file_path.name}")
        logger.info("-" * 70)
        
        process_file_recursive(file_path)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Files processed: {stats['files_processed']}")
    logger.info(f"Files split: {stats['files_split']}")
    logger.info(f"Total segments created: {stats['segments_created']}")
    logger.info(f"Recursion levels used:")
    for level, count in sorted(stats['recursion_levels'].items()):
        logger.info(f"  Level {level}: {count} files")
    
    if stats['files_failed']:
        logger.warning(f"\n⚠️  {len(stats['files_failed'])} files failed:")
        for failed_file in stats['files_failed']:
            logger.warning(f"  - {failed_file}")
    else:
        logger.info("\n✅ All files successfully ingested!")
    
    logger.info("=" * 70)
    
    return 0 if not stats['files_failed'] else 1


if __name__ == "__main__":
    sys.exit(main())

