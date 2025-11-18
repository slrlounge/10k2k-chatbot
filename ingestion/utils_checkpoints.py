"""
Checkpoint utilities for tracking processed files.
Uses JSON file for persistence.
"""

import json
import os
from pathlib import Path
from typing import Set


def get_checkpoint_file() -> Path:
    """Get the checkpoint file path from environment or default."""
    checkpoint_path = os.getenv('CHECKPOINT_FILE', '/app/checkpoints/ingest_transcripts.json')
    checkpoint_file = Path(checkpoint_path)
    
    # Fallback to local checkpoints/ if /app/checkpoints doesn't exist
    if not checkpoint_file.parent.exists():
        checkpoint_file = Path('checkpoints') / 'ingest_transcripts.json'
    
    # Ensure directory exists
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    
    return checkpoint_file


def get_processed() -> Set[str]:
    """
    Load set of processed file paths from checkpoint.
    
    Returns:
        Set of file paths (as strings) that have been processed
    """
    checkpoint_file = get_checkpoint_file()
    
    if not checkpoint_file.exists():
        return set()
    
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('processed', []))
    except (json.JSONDecodeError, IOError):
        return set()


def mark_processed(file_path: str, success: bool = True):
    """
    Mark a file as processed in the checkpoint.
    
    Args:
        file_path: Path to the file (as string)
        success: True if processed successfully, False if skipped/failed
    """
    checkpoint_file = get_checkpoint_file()
    
    # Load existing data
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {'processed': [], 'skipped': []}
    else:
        data = {'processed': [], 'skipped': []}
    
    # Update sets
    processed = set(data.get('processed', []))
    skipped = set(data.get('skipped', []))
    
    if success:
        processed.add(file_path)
        skipped.discard(file_path)  # Remove from skipped if it was there
    else:
        skipped.add(file_path)
        processed.discard(file_path)  # Remove from processed if it was there
    
    # Save updated data
    data['processed'] = sorted(list(processed))
    data['skipped'] = sorted(list(skipped))
    
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_processed(file_path: str) -> bool:
    """
    Check if a file has already been processed.
    
    Args:
        file_path: Path to the file (as string)
    
    Returns:
        True if file is in processed set
    """
    processed = get_processed()
    return file_path in processed

