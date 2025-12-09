#!/usr/bin/env python3
"""
Automatic File Chunker
Splits large files that fail ingestion into smaller parts.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import tiktoken
from dotenv import load_dotenv

load_dotenv()

TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2Kv2'))
MAX_CHUNK_SIZE_MB = 0.01  # 10KB per chunk (very conservative)
MAX_CHUNK_TOKENS = 500

tokenizer = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))


def split_at_semantic_boundaries(text: str, max_tokens: int) -> List[str]:
    """Split text at semantic boundaries (paragraphs, sentences, clauses)."""
    chunks = []
    
    # First try splitting by double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if para_tokens > max_tokens:
            # Paragraph too large, split by sentences
            sentences = para.split('. ')
            for sent in sentences:
                sent_tokens = count_tokens(sent)
                
                if sent_tokens > max_tokens:
                    # Sentence too large, split by clauses
                    clauses = sent.split(', ')
                    for clause in clauses:
                        clause_tokens = count_tokens(clause)
                        if current_tokens + clause_tokens > max_tokens and current_chunk:
                            chunks.append(' '.join(current_chunk))
                            current_chunk = [clause]
                            current_tokens = clause_tokens
                        else:
                            current_chunk.append(clause)
                            current_tokens += clause_tokens
                else:
                    if current_tokens + sent_tokens > max_tokens and current_chunk:
                        chunks.append('. '.join(current_chunk))
                        current_chunk = [sent]
                        current_tokens = sent_tokens
                    else:
                        current_chunk.append(sent)
                        current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > max_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def create_segment_filename(original_file: Path, segment_num: int) -> Path:
    """Create segment filename with zero-padded numbering."""
    stem = original_file.stem
    suffix = original_file.suffix
    
    # Check if already has segment number
    if '_' in stem and stem.split('_')[-1].isdigit():
        base = '_'.join(stem.split('_')[:-1])
    else:
        base = stem
    
    segment_name = f"{base}_{segment_num:02d}{suffix}"
    return original_file.parent / segment_name


def split_file(file_path: Path) -> List[Path]:
    """Split a file into smaller segments."""
    print(f"Splitting file: {file_path}")
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return []
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Calculate target size
    max_bytes = int(MAX_CHUNK_SIZE_MB * 1024 * 1024)
    content_bytes = len(content.encode('utf-8'))
    
    if content_bytes <= max_bytes:
        print(f"File is already small enough ({content_bytes} bytes)")
        return [file_path]
    
    # Split into chunks
    chunks = split_at_semantic_boundaries(content, MAX_CHUNK_TOKENS)
    
    # Create segment files
    segment_files = []
    for i, chunk in enumerate(chunks, 1):
        segment_path = create_segment_filename(file_path, i)
        
        with open(segment_path, 'w', encoding='utf-8') as f:
            f.write(chunk)
        
        segment_files.append(segment_path)
        print(f"  Created segment {i}/{len(chunks)}: {segment_path.name} ({len(chunk.encode('utf-8'))} bytes)")
    
    # Move original to backup (optional)
    backup_path = file_path.parent / f"{file_path.name}.backup"
    if backup_path.exists():
        backup_path.unlink()
    file_path.rename(backup_path)
    print(f"  Original backed up to: {backup_path.name}")
    
    return segment_files


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 auto_chunker.py <file_path>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    if not file_path.is_absolute():
        file_path = TRANSCRIPTS_DIR / file_path
    
    segments = split_file(file_path)
    
    if segments:
        print(f"\n✓ Successfully split into {len(segments)} segments")
        return 0
    else:
        print("\n✗ Failed to split file")
        return 1


if __name__ == "__main__":
    sys.exit(main())

