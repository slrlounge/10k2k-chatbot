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
    
    # Log checkpoint path for debugging
    import logging
    logger = logging.getLogger('checkpoints')
    logger.info(f"Checkpoint file path: {checkpoint_file}")
    logger.info(f"Checkpoint file parent exists: {checkpoint_file.parent.exists()}")
    logger.info(f"CHECKPOINT_FILE env var: {os.getenv('CHECKPOINT_FILE', 'NOT SET')}")
    
    # Fallback to local checkpoints/ if /app/checkpoints doesn't exist
    if not checkpoint_file.parent.exists():
        logger.warning(f"Checkpoint parent doesn't exist, trying fallback")
        checkpoint_file = Path('checkpoints') / 'ingest_transcripts.json'
        logger.info(f"Fallback checkpoint path: {checkpoint_file}")
    
    # Ensure directory exists
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Checkpoint directory ensured: {checkpoint_file.parent}")
    
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
    import logging
    logger = logging.getLogger('checkpoints')
    
    checkpoint_file = get_checkpoint_file()
    logger.info(f"Marking {file_path} as processed: {success}")
    logger.info(f"Using checkpoint file: {checkpoint_file}")
    
    # Load existing data
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded existing checkpoint with {len(data.get('processed', []))} processed files")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading checkpoint: {e}, starting fresh")
            data = {'processed': [], 'skipped': []}
    else:
        logger.info("Checkpoint file doesn't exist, creating new one")
        data = {'processed': [], 'skipped': []}
    
    # Update sets
    processed = set(data.get('processed', []))
    skipped = set(data.get('skipped', []))
    
    if success:
        processed.add(file_path)
        skipped.discard(file_path)  # Remove from skipped if it was there
        logger.info(f"Added {file_path} to processed set (now {len(processed)} files)")
    else:
        skipped.add(file_path)
        processed.discard(file_path)  # Remove from processed if it was there
        logger.info(f"Added {file_path} to skipped set")
    
    # Save updated data
    data['processed'] = sorted(list(processed))
    data['skipped'] = sorted(list(skipped))
    
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Checkpoint saved successfully to {checkpoint_file}")
        logger.info(f"Checkpoint contains {len(data['processed'])} processed files")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


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

