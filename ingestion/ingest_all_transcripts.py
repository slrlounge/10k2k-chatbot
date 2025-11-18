#!/usr/bin/env python3
"""
Transcript Ingestion Orchestrator
Scans for transcript files and processes each one in a separate Python process.
This ensures complete memory release between files and prevents OOM kills.
Designed for Docker, restart-safe with checkpoint system.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

try:
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import get_processed
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingestion.utils_logging import setup_logger
    from ingestion.utils_checkpoints import get_processed

# Load environment variables
load_dotenv()

# Configuration from environment
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/transcripts'))
INGEST_SCRIPT = Path(os.getenv('INGEST_SCRIPT', '/app/ingestion/ingest_single_transcript.py'))
INGEST_SCRIPT_ADAPTIVE = Path(os.getenv('INGEST_SCRIPT_ADAPTIVE', '/app/ingestion/ingest_single_transcript_adaptive.py'))
INGEST_SCRIPT_DIRECT = Path(os.getenv('INGEST_SCRIPT_DIRECT', '/app/ingestion/ingest_single_transcript_direct.py'))
INGEST_SCRIPT_MINIMAL = Path(os.getenv('INGEST_SCRIPT_MINIMAL', '/app/ingestion/ingest_single_transcript_minimal.py'))
INGEST_SCRIPT_ULTRA_MINIMAL = Path(os.getenv('INGEST_SCRIPT_ULTRA_MINIMAL', '/app/ingestion/ingest_single_transcript_ultra_minimal.py'))
PYTHON_CMD = os.getenv('PYTHON_CMD', 'python3')
USE_ADAPTIVE = os.getenv('USE_ADAPTIVE', 'true').lower() == 'true'
USE_DIRECT_API = os.getenv('USE_DIRECT_API', 'false').lower() == 'true'
USE_MINIMAL = os.getenv('USE_MINIMAL', 'true').lower() == 'true'
USE_ULTRA_MINIMAL = os.getenv('USE_ULTRA_MINIMAL', 'true').lower() == 'true'  # Auto-fallback to ultra-minimal
MAX_RETRIES_PER_FILE = int(os.getenv('MAX_RETRIES_PER_FILE', '3'))  # Try up to 3 different approaches

# Initialize logger
logger = setup_logger('ingest_all')


def find_transcript_files() -> list:
    """
    Recursively find all .txt transcript files in TRANSCRIPTS_DIR.
    
    Returns:
        List of Path objects for transcript files
    """
    if not TRANSCRIPTS_DIR.exists():
        logger.error(f"Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
        return []
    
    # Recursively find all .txt files
    transcript_files = sorted([f for f in TRANSCRIPTS_DIR.rglob('*.txt') if f.is_file()])
    logger.info(f"Found {len(transcript_files)} transcript files in {TRANSCRIPTS_DIR}")
    
    return transcript_files


def process_file_in_subprocess(file_path: Path, attempt: int = 1) -> bool:
    """
    Process a single file by spawning a new Python process.
    Automatically tries progressively more aggressive approaches if files fail.
    
    Args:
        file_path: Path to transcript file
        attempt: Current attempt number (for retry logic)
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Spawning subprocess for: {file_path.name} (attempt {attempt}/{MAX_RETRIES_PER_FILE})")
    
    # Progressive fallback strategy: try less aggressive first, then more aggressive
    scripts_to_try = []
    
    if attempt == 1:
        # First attempt: try minimal (balanced)
        if USE_MINIMAL and INGEST_SCRIPT_MINIMAL.exists():
            scripts_to_try.append(INGEST_SCRIPT_MINIMAL)
        elif USE_ADAPTIVE and INGEST_SCRIPT_ADAPTIVE.exists():
            scripts_to_try.append(INGEST_SCRIPT_ADAPTIVE)
        else:
            scripts_to_try.append(INGEST_SCRIPT)
    
    elif attempt == 2:
        # Second attempt: try ultra-minimal (most aggressive)
        if USE_ULTRA_MINIMAL and INGEST_SCRIPT_ULTRA_MINIMAL.exists():
            scripts_to_try.append(INGEST_SCRIPT_ULTRA_MINIMAL)
        elif USE_ADAPTIVE and INGEST_SCRIPT_ADAPTIVE.exists():
            scripts_to_try.append(INGEST_SCRIPT_ADAPTIVE)
        elif USE_MINIMAL and INGEST_SCRIPT_MINIMAL.exists():
            scripts_to_try.append(INGEST_SCRIPT_MINIMAL)
    
    elif attempt == 3:
        # Third attempt: try adaptive with different chunk sizes
        if USE_ADAPTIVE and INGEST_SCRIPT_ADAPTIVE.exists():
            scripts_to_try.append(INGEST_SCRIPT_ADAPTIVE)
        elif USE_ULTRA_MINIMAL and INGEST_SCRIPT_ULTRA_MINIMAL.exists():
            scripts_to_try.append(INGEST_SCRIPT_ULTRA_MINIMAL)
    
    # Fallback to regular script if nothing else available
    if not scripts_to_try:
        scripts_to_try.append(INGEST_SCRIPT)
    
    script_to_use = scripts_to_try[0]
    
    try:
        # Run ingest script in a fresh Python process
        result = subprocess.run(
            [PYTHON_CMD, str(script_to_use), str(file_path)],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout (ultra-minimal takes longer)
        )
        
        # Log output
        if result.stdout:
            logger.info(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully processed: {file_path.name} (attempt {attempt})")
            return True
        else:
            # Check if it's an OOM kill (exit code -9) or timeout
            exit_code = result.returncode
            if exit_code == -9 or exit_code == 137:
                logger.warning(f"⚠️  OOM kill detected (exit {exit_code}) for {file_path.name} on attempt {attempt}")
            elif exit_code == 143:
                logger.warning(f"⚠️  Timeout detected (exit {exit_code}) for {file_path.name} on attempt {attempt}")
            else:
                logger.warning(f"⚠️  Error (exit {exit_code}) for {file_path.name} on attempt {attempt}")
            
            # Retry with more aggressive approach if we have attempts left
            if attempt < MAX_RETRIES_PER_FILE:
                next_attempt = attempt + 1
                logger.info(f"🔄 Retrying {file_path.name} with more aggressive approach (attempt {next_attempt}/{MAX_RETRIES_PER_FILE})...")
                time.sleep(2)  # Brief pause before retry
                return process_file_in_subprocess(file_path, next_attempt)
            else:
                logger.error(f"✗ Failed to process: {file_path.name} after {MAX_RETRIES_PER_FILE} attempts (exit code {exit_code})")
                return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout processing: {file_path.name} (attempt {attempt})")
        if attempt < MAX_RETRIES_PER_FILE:
            logger.info(f"Retrying {file_path.name} with more aggressive approach...")
            return process_file_in_subprocess(file_path, attempt + 1)
        return False
    except Exception as e:
        logger.error(f"✗ Error spawning subprocess for {file_path.name}: {e}")
        return False


def send_completion_notification(total_files, already_processed, newly_processed, failed):
    """Send a system notification when ingestion completes."""
    try:
        # Try macOS notification
        if sys.platform == 'darwin':
            status = "✅ COMPLETE" if failed == 0 else "⚠️ COMPLETE WITH ERRORS"
            message = f"Processed {newly_processed} new files ({total_files} total)"
            if failed > 0:
                message += f", {failed} failed"
            
            osascript_cmd = f'''
            osascript -e 'display notification "{message}" with title "Ingestion {status}" sound name "Glass"'
            '''
            subprocess.run(osascript_cmd, shell=True, capture_output=True)
            logger.info(f"📢 Notification sent: {status}")
        else:
            # For non-macOS, just log prominently
            logger.info("=" * 60)
            logger.info("🎉 INGESTION COMPLETE!")
            logger.info("=" * 60)
    except Exception as e:
        logger.debug(f"Could not send notification: {e}")


def wait_for_chromadb(max_wait=60):
    """Wait for ChromaDB server to be ready."""
    import time
    import chromadb
    
    logger.info("Waiting for ChromaDB server to be ready...")
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
    CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            client.heartbeat()  # Test connection
            logger.info("ChromaDB server is ready!")
            return True
        except Exception as e:
            logger.debug(f"ChromaDB not ready yet: {e}")
            time.sleep(2)
    
    logger.error(f"ChromaDB server not ready after {max_wait} seconds")
    return False


def main():
    """Main orchestration function."""
    logger.info("=" * 60)
    logger.info("Transcript Ingestion Pipeline")
    logger.info("=" * 60)
    
    # Wait for ChromaDB to be ready
    if not wait_for_chromadb():
        logger.error("Cannot proceed without ChromaDB server")
        return 1
    
    # Find all transcript files
    all_files = find_transcript_files()
    
    if not all_files:
        logger.warning("No transcript files found!")
        return 0
    
    # Get already processed files
    processed = get_processed()
    logger.info(f"Found {len(processed)} files already processed in checkpoint")
    
    # Filter out already processed files
    files_to_process = [
        f for f in all_files 
        if str(f) not in processed
    ]
    
    total_files = len(all_files)
    remaining = len(files_to_process)
    
    logger.info(f"Total files: {total_files}")
    logger.info(f"Already processed: {len(processed)}")
    logger.info(f"Remaining to process: {remaining}")
    
    if not files_to_process:
        logger.info("=" * 60)
        logger.info("✅ All files have been processed!")
        logger.info("=" * 60)
        send_completion_notification(total_files, len(processed), 0, 0)
        return 0
    
    # Process each file in a separate subprocess
    successful = 0
    failed = 0
    
    logger.info("=" * 60)
    logger.info("Starting ingestion...")
    logger.info("=" * 60)
    
    for i, file_path in enumerate(files_to_process, 1):
        logger.info(f"\n[{i}/{remaining}] Processing: {file_path.name}")
        
        # Process with automatic retry logic
        if process_file_in_subprocess(file_path, attempt=1):
            successful += 1
        else:
            failed += 1
        
        # Progress update
        logger.info(f"Progress: {i}/{remaining} files processed ({successful} successful, {failed} failed)")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Ingestion Summary:")
    logger.info(f"  Total files: {total_files}")
    logger.info(f"  Already processed: {len(processed)}")
    logger.info(f"  Newly processed: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info("=" * 60)
    
    # Send completion notification (macOS)
    send_completion_notification(total_files, len(processed), successful, failed)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main() or 0)

