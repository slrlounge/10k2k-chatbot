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
USE_ADAPTIVE = os.getenv('USE_ADAPTIVE', 'false').lower() == 'true'
USE_DIRECT_API = os.getenv('USE_DIRECT_API', 'false').lower() == 'true'
USE_MINIMAL = os.getenv('USE_MINIMAL', 'false').lower() == 'true'
# Default to ultra-minimal if no preference set (safest option)
USE_ULTRA_MINIMAL = os.getenv('USE_ULTRA_MINIMAL', 'true').lower() == 'true'  # Default to ultra-minimal for safety
MAX_RETRIES_PER_FILE = int(os.getenv('MAX_RETRIES_PER_FILE', '3'))  # Try up to 3 different approaches

# Initialize logger
logger = setup_logger('ingest_all')


def find_transcript_files() -> list:
    """
    Recursively find all .txt transcript files in TRANSCRIPTS_DIR.
    Returns files sorted by size (smallest first) and skips files larger than MAX_FILE_SIZE_MB.
    
    Returns:
        List of Path objects for transcript files, sorted by size (smallest first)
    """
    MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', '10.0'))
    
    if not TRANSCRIPTS_DIR.exists():
        logger.error(f"Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
        return []
    
    transcript_files = []
    skipped_large = []
    
    # Recursively find all .txt files and check sizes
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            try:
                file_size_mb = txt_file.stat().st_size / (1024 * 1024)
                
                if file_size_mb > MAX_FILE_SIZE_MB:
                    logger.warning(f"Skipping large file: {txt_file.name} ({file_size_mb:.2f}MB > {MAX_FILE_SIZE_MB}MB)")
                    skipped_large.append((txt_file, file_size_mb))
                else:
                    transcript_files.append(txt_file)
            except Exception as e:
                logger.warning(f"Error checking size for {txt_file.name}: {e}, skipping")
                continue
    
    # Sort by file size (smallest first) for easier debugging
    transcript_files.sort(key=lambda f: f.stat().st_size)
    
    logger.info(f"Found {len(transcript_files)} transcript files in {TRANSCRIPTS_DIR}")
    
    if skipped_large:
        logger.info(f"Skipped {len(skipped_large)} files larger than {MAX_FILE_SIZE_MB}MB:")
        for file_path, size_mb in skipped_large[:5]:  # Show first 5
            logger.info(f"  - {file_path.name}: {size_mb:.2f}MB")
        if len(skipped_large) > 5:
            logger.info(f"  ... and {len(skipped_large) - 5} more")
    
    # Log file sizes for first few files (processing order)
    if transcript_files:
        logger.info("Processing order (smallest first):")
        for i, file_path in enumerate(transcript_files[:10], 1):
            try:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                logger.info(f"  {i}. {file_path.name}: {size_mb:.2f}MB")
            except Exception:
                logger.info(f"  {i}. {file_path.name}: (size unknown)")
        if len(transcript_files) > 10:
            logger.info(f"  ... and {len(transcript_files) - 10} more files")
    
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
        # First attempt: try ultra-minimal first (safest, most memory-efficient)
        if USE_ULTRA_MINIMAL and INGEST_SCRIPT_ULTRA_MINIMAL.exists():
            scripts_to_try.append(INGEST_SCRIPT_ULTRA_MINIMAL)
        elif USE_MINIMAL and INGEST_SCRIPT_MINIMAL.exists():
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
    
    # Force flush logs before subprocess
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        # Log subprocess start - CRITICAL: Log before subprocess.run()
        logger.info(f"Starting subprocess: {PYTHON_CMD} {script_to_use} {file_path}")
        logger.info(f"Subprocess timeout: 1800 seconds (30 minutes)")
        logger.info(f"About to call subprocess.run()...")
        
        # Force flush again
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Run ingest script in a fresh Python process
        logger.info(f"Calling subprocess.run() NOW...")
        result = subprocess.run(
            [PYTHON_CMD, str(script_to_use), str(file_path)],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout (ultra-minimal takes longer)
        )
        logger.info(f"subprocess.run() RETURNED!")
        
        # Log subprocess completion immediately
        logger.info(f"Subprocess completed with returncode: {result.returncode}")
        
        # Log output (always log, even if empty)
        if result.stdout:
            stdout_preview = result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout
            logger.info(f"Subprocess stdout ({len(result.stdout)} chars):\n{stdout_preview}")
            if len(result.stdout) > 1000:
                logger.info(f"... (truncated, showing first 1000 chars)")
        else:
            logger.warning("Subprocess stdout is EMPTY - no output from script!")
        
        if result.stderr:
            stderr_preview = result.stderr[:1000] if len(result.stderr) > 1000 else result.stderr
            logger.warning(f"Subprocess stderr ({len(result.stderr)} chars):\n{stderr_preview}")
            if len(result.stderr) > 1000:
                logger.warning(f"... (truncated, showing first 1000 chars)")
        else:
            logger.info("Subprocess stderr is empty (no errors)")
        
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
            
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Timeout processing: {file_path.name} (attempt {attempt})")
        logger.warning(f"Timeout exception: {e}")
        if attempt < MAX_RETRIES_PER_FILE:
            logger.info(f"Retrying {file_path.name} with more aggressive approach...")
            return process_file_in_subprocess(file_path, attempt + 1)
        return False
    except Exception as e:
        logger.error(f"✗ Error spawning subprocess for {file_path.name}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
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
            # For HTTPS (port 443), ChromaDB HttpClient should handle it
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            # Try to list collections (works with v2 API)
            try:
                client.list_collections()
                logger.info("ChromaDB server is ready!")
                return True
            except Exception as e:
                # If list_collections fails, try heartbeat as fallback
                try:
                    client.heartbeat()
                    logger.info("ChromaDB server is ready!")
                    return True
                except Exception as e2:
                    # Log but continue - might be API version issue
                    logger.debug(f"Connection test failed: {e2}")
                    # Still return True if we can create a client (connection works)
                    logger.info("ChromaDB server appears ready (connection successful)")
                    return True
        except Exception as e:
            logger.debug(f"ChromaDB not ready yet: {e}")
            time.sleep(2)
    
    logger.warning(f"ChromaDB connection test timed out, but continuing anyway...")
    logger.info("If ingestion fails, check ChromaDB service status")
    return True  # Continue anyway - let ingestion scripts handle connection errors


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
        logger.info(f"About to call process_file_in_subprocess for: {file_path}")
        
        try:
            # Process with automatic retry logic
            result = process_file_in_subprocess(file_path, attempt=1)
            logger.info(f"process_file_in_subprocess returned: {result}")
            if result:
                successful += 1
                logger.info(f"✓ File {i} processed successfully")
            else:
                failed += 1
                logger.warning(f"✗ File {i} failed to process")
        except Exception as e:
            logger.error(f"✗ Exception in main loop processing {file_path.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

