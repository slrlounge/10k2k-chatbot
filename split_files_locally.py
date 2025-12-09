#!/usr/bin/env python3
"""
Local File Splitting Script
Splits transcript files into 0.01MB (10KB) segments before ingestion.
Keeps files organized and named logically (e.g., sales_01.txt, sales_02.txt).
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

# Configuration
TRANSCRIPTS_DIR = Path('10K2Kv2')
MAX_SEGMENT_SIZE_BYTES = 10 * 1024  # 0.01MB = 10KB
BACKUP_ORIGINALS = True  # Keep original files in a backup directory

stats = {
    'files_processed': 0,
    'files_split': 0,
    'segments_created': 0,
    'files_skipped': 0,
    'total_original_size_mb': 0,
    'total_segments_size_mb': 0
}


def split_at_semantic_boundaries(content: str, target_size_bytes: int) -> List[str]:
    """Split text at semantic boundaries (paragraphs, lines, sentences, clauses)."""
    segments = []
    paragraphs = content.split('\n\n')
    current_segment = ""
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para.encode('utf-8'))
        
        # If paragraph itself is too large, split by lines
        if para_size > target_size_bytes:
            lines = para.split('\n')
            for line in lines:
                line_size = len(line.encode('utf-8'))
                
                # If line is too large, split by sentences
                if line_size > target_size_bytes:
                    sentences = re.split(r'(?<=[.!?])\s+', line)
                    for sentence in sentences:
                        sent_size = len(sentence.encode('utf-8'))
                        
                        # If sentence is too large, split by clauses
                        if sent_size > target_size_bytes:
                            clauses = re.split(r'(?<=[,;:])\s+', sentence)
                            for clause in clauses:
                                clause_size = len(clause.encode('utf-8'))
                                
                                # Add clause to current segment or start new one
                                if current_size + clause_size > target_size_bytes and current_segment:
                                    segments.append(current_segment.strip())
                                    current_segment = clause
                                    current_size = clause_size
                                else:
                                    current_segment += (" " + clause if current_segment else clause)
                                    current_size += clause_size
                        else:
                            # Add sentence to current segment or start new one
                            if current_size + sent_size > target_size_bytes and current_segment:
                                segments.append(current_segment.strip())
                                current_segment = sentence
                                current_size = sent_size
                            else:
                                current_segment += (" " + sentence if current_segment else sentence)
                                current_size += sent_size
                else:
                    # Add line to current segment or start new one
                    if current_size + line_size > target_size_bytes and current_segment:
                        segments.append(current_segment.strip())
                        current_segment = line
                        current_size = line_size
                    else:
                        current_segment += ("\n" + line if current_segment else line)
                        current_size += line_size
        else:
            # Add paragraph to current segment or start new one
            if current_size + para_size > target_size_bytes and current_segment:
                segments.append(current_segment.strip())
                current_segment = para
                current_size = para_size
            else:
                current_segment += ("\n\n" + para if current_segment else para)
                current_size += para_size
    
    # Add final segment
    if current_segment.strip():
        segments.append(current_segment.strip())
    
    return segments


def create_segment_file(original_file: Path, segment_num: int, content: str) -> Path:
    """Create a segment file with proper naming convention."""
    base_name = original_file.stem
    extension = original_file.suffix
    segment_name = f"{base_name}_{segment_num:02d}{extension}"
    segment_path = original_file.parent / segment_name
    segment_path.write_text(content, encoding='utf-8')
    return segment_path


def backup_original_file(file_path: Path, backup_dir: Path) -> Path:
    """Move original file to backup directory."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    relative_path = file_path.relative_to(TRANSCRIPTS_DIR)
    backup_path = backup_dir / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), str(backup_path))
    return backup_path


def process_file(file_path: Path, backup_dir: Path) -> Tuple[bool, int]:
    """Process a single file: split if needed, return (was_split, num_segments)."""
    file_size_bytes = file_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    stats['total_original_size_mb'] += file_size_mb
    
    # If file is small enough, skip it
    if file_size_bytes <= MAX_SEGMENT_SIZE_BYTES:
        print(f"  ✓ Skipping (already small): {file_path.name} ({file_size_mb:.3f}MB)")
        stats['files_skipped'] += 1
        return False, 1
    
    print(f"  📄 Processing: {file_path.name} ({file_size_mb:.3f}MB)")
    
    # Read file content
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return False, 0
    
    # Split into segments
    segments = split_at_semantic_boundaries(content, MAX_SEGMENT_SIZE_BYTES)
    
    if len(segments) <= 1:
        print(f"  ⚠️  Could not split further, keeping original")
        stats['files_skipped'] += 1
        return False, 1
    
    print(f"     → Splitting into {len(segments)} segments...")
    
    # Create segment files
    segment_files = []
    total_segments_size = 0
    
    for i, segment_content in enumerate(segments, 1):
        segment_file = create_segment_file(file_path, i, segment_content)
        segment_files.append(segment_file)
        segment_size = segment_file.stat().st_size
        total_segments_size += segment_size
        stats['segments_created'] += 1
    
    # Backup original file
    if BACKUP_ORIGINALS:
        backup_path = backup_original_file(file_path, backup_dir)
        try:
            backup_relative = backup_path.relative_to(Path.cwd())
            print(f"     → Original backed up to: {backup_relative}")
        except ValueError:
            print(f"     → Original backed up to: {backup_path}")
    
    stats['files_split'] += 1
    stats['total_segments_size_mb'] += (total_segments_size / (1024 * 1024))
    
    print(f"     ✓ Created {len(segments)} segments")
    return True, len(segments)


def main():
    """Main orchestration function."""
    print("=" * 70)
    print("LOCAL FILE SPLITTING - PRE-INGESTION")
    print("=" * 70)
    print(f"Source directory: {TRANSCRIPTS_DIR}")
    print(f"Max segment size: {MAX_SEGMENT_SIZE_BYTES / 1024:.2f}KB (0.01MB)")
    print(f"Backup originals: {BACKUP_ORIGINALS}")
    print()
    
    # Check if transcripts directory exists
    if not TRANSCRIPTS_DIR.exists():
        print(f"✗ Error: Directory '{TRANSCRIPTS_DIR}' does not exist!")
        return 1
    
    # Create backup directory
    backup_dir = Path('10K2K v2_backup')
    if BACKUP_ORIGINALS:
        print(f"Backup directory: {backup_dir}")
        print()
    
    # Find all .txt files
    print("Scanning for transcript files...")
    txt_files = list(TRANSCRIPTS_DIR.rglob('*.txt'))
    print(f"Found {len(txt_files)} transcript files")
    print()
    
    if not txt_files:
        print("No transcript files found!")
        return 0
    
    # Process each file
    print("=" * 70)
    print("PROCESSING FILES")
    print("=" * 70)
    print()
    
    for i, file_path in enumerate(txt_files, 1):
        print(f"[{i}/{len(txt_files)}] {file_path.relative_to(TRANSCRIPTS_DIR)}")
        was_split, num_segments = process_file(file_path, backup_dir)
        stats['files_processed'] += 1
        print()
    
    # Print summary
    print("=" * 70)
    print("SPLITTING SUMMARY")
    print("=" * 70)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files split: {stats['files_split']}")
    print(f"Files skipped (already small): {stats['files_skipped']}")
    print(f"Total segments created: {stats['segments_created']}")
    print(f"Original total size: {stats['total_original_size_mb']:.2f}MB")
    print(f"Segments total size: {stats['total_segments_size_mb']:.2f}MB")
    
    if BACKUP_ORIGINALS:
        print(f"\nOriginal files backed up to: {backup_dir}")
    
    print()
    print("=" * 70)
    print("✅ FILE SPLITTING COMPLETE")
    print("=" * 70)
    print()
    print("Next step: Run ingestion script to upload all segments to ChromaDB")
    print()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

