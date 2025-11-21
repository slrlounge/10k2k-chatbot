#!/usr/bin/env python3
"""
Video Transcription Script
Uses OpenAI Whisper API to transcribe video/audio files to text.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Directories - can be overridden via environment variables
SOURCE_DATA_DIR = Path(os.getenv('SOURCE_DATA_DIR', 'data'))
# Default to the 10K2K v2 folder if VIDEO_DIR is not set
VIDEO_DIR = Path(os.getenv('VIDEO_DIR', '/Users/justinlin/Documents/10K2KChatBot/10K2Kv2'))
TRANSCRIPT_DIR = Path(os.getenv('TRANSCRIPT_DIR', str(SOURCE_DATA_DIR / 'transcripts')))

# Supported video/audio file extensions
SUPPORTED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v',
                        '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma'}

# Maximum file size for OpenAI API (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes

# Chunk size for splitting large files (slightly under 25MB to be safe)
CHUNK_SIZE_TARGET = 23 * 1024 * 1024  # 23MB in bytes


def get_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key from environment."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables!")
        print("Please add OPENAI_API_KEY to your .env file:")
        print("  OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    return OpenAI(api_key=api_key)


def get_video_files() -> List[Path]:
    """Recursively scan VIDEO_DIR for supported video/audio files."""
    if not VIDEO_DIR.exists():
        print(f"ERROR: Video directory '{VIDEO_DIR}' does not exist!")
        sys.exit(1)
    
    # Use rglob to recursively search for video files in all subdirectories
    video_files = []
    for ext in SUPPORTED_EXTENSIONS:
        video_files.extend(VIDEO_DIR.rglob(f'*{ext}'))
    
    # Filter to only files (not directories) and sort
    video_files = [f for f in video_files if f.is_file()]
    return sorted(video_files)


def get_transcript_path(video_file: Path) -> Path:
    """Generate transcript file path from video file path.
    Saves transcript next to the video file (same directory) for better organization.
    """
    # Replace video extension with .txt, keep in same directory as video
    transcript_name = video_file.stem + '.txt'
    return video_file.parent / transcript_name


def file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    return file_path.stat().st_size / (1024 * 1024)


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available on the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_video_duration(video_file: Path) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
             str(video_file)],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def split_video_into_chunks(video_file: Path, temp_dir: Path) -> List[Path]:
    """Split a large video file into chunks under 25MB.
    Returns list of chunk file paths.
    """
    duration = get_video_duration(video_file)
    file_size = video_file.stat().st_size
    
    if duration is None:
        raise ValueError("Could not determine video duration. ffprobe may not be installed.")
    
    # Estimate bytes per second
    bytes_per_second = file_size / duration
    
    # Calculate chunk duration to target ~23MB per chunk
    chunk_duration_seconds = CHUNK_SIZE_TARGET / bytes_per_second
    
    # Round to nearest 10 seconds for cleaner splits
    chunk_duration_seconds = max(10, int(chunk_duration_seconds / 10) * 10)
    
    chunks = []
    start_time = 0
    chunk_num = 0
    
    print(f"    Splitting into ~{int(duration / chunk_duration_seconds) + 1} chunks...", end='', flush=True)
    
    while start_time < duration:
        chunk_num += 1
        chunk_path = temp_dir / f"chunk_{chunk_num:03d}.mp4"
        
        # Use ffmpeg to extract a segment
        try:
            subprocess.run(
                ['ffmpeg', '-i', str(video_file),
                 '-ss', str(start_time),
                 '-t', str(chunk_duration_seconds),
                 '-c', 'copy',  # Copy codec to avoid re-encoding (faster)
                 '-avoid_negative_ts', 'make_zero',
                 str(chunk_path)],
                capture_output=True,
                check=True
            )
            
            # Check if chunk is still too large (may happen with variable bitrate)
            if chunk_path.exists() and chunk_path.stat().st_size > MAX_FILE_SIZE:
                # Re-encode with lower bitrate if needed
                chunk_path.unlink()
                subprocess.run(
                    ['ffmpeg', '-i', str(video_file),
                     '-ss', str(start_time),
                     '-t', str(chunk_duration_seconds),
                     '-b:v', '500k',  # Lower bitrate
                     '-b:a', '64k',
                     str(chunk_path)],
                    capture_output=True,
                    check=True
                )
            
            if chunk_path.exists() and chunk_path.stat().st_size > 0:
                chunks.append(chunk_path)
            
            start_time += chunk_duration_seconds
            
        except subprocess.CalledProcessError as e:
            print(f"\n    Warning: Error creating chunk {chunk_num}: {e}")
            break
    
    print(f" ✓ ({len(chunks)} chunks)")
    return chunks


def transcribe_large_file(client: OpenAI, video_file: Path) -> str:
    """Transcribe a large video file by splitting it into chunks."""
    if not check_ffmpeg():
        raise ValueError(
            "ffmpeg is not installed. Please install ffmpeg to process large files.\n"
            "macOS: brew install ffmpeg\n"
            "Linux: sudo apt-get install ffmpeg\n"
            "Windows: Download from https://ffmpeg.org/download.html"
        )
    
    # Create temporary directory for chunks
    temp_dir = Path(tempfile.mkdtemp(prefix='video_chunks_'))
    all_transcripts = []
    
    try:
        # Split video into chunks
        chunks = split_video_into_chunks(video_file, temp_dir)
        
        if not chunks:
            raise ValueError("Failed to create video chunks")
        
        # Transcribe each chunk
        print(f"    Transcribing {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks, 1):
            chunk_size_mb = file_size_mb(chunk)
            print(f"      Chunk {i}/{len(chunks)} ({chunk_size_mb:.2f}MB)...", end='', flush=True)
            
            try:
                with open(chunk, 'rb') as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                all_transcripts.append(transcript.strip())
                print(" ✓")
            except Exception as e:
                print(f" ✗ Error: {e}")
                # Continue with other chunks even if one fails
                continue
        
        # Combine all transcripts
        combined_transcript = "\n\n".join(all_transcripts)
        return combined_transcript
        
    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def transcribe_file(client: OpenAI, video_file: Path) -> str:
    """Transcribe a video/audio file using OpenAI Whisper API."""
    file_size = video_file.stat().st_size
    
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size ({file_size_mb(video_file):.2f}MB) exceeds maximum ({MAX_FILE_SIZE / (1024*1024):.2f}MB)")
    
    print(f"    Uploading file ({file_size_mb(video_file):.2f}MB)...", end='', flush=True)
    
    try:
        with open(video_file, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        print(" ✓")
        return transcript.strip()
    
    except Exception as e:
        print(f" ✗")
        raise e


def main():
    """Main function to transcribe all videos."""
    print("Video Transcription Script (OpenAI Whisper API)")
    print("=" * 60)
    
    # Ensure transcript directory exists
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize OpenAI client
    print("\n[1/3] Initializing OpenAI client...")
    try:
        client = get_openai_client()
        print("✓ Client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        sys.exit(1)
    
    # Get video files
    print(f"\n[2/3] Scanning {VIDEO_DIR} for video/audio files (recursively)...")
    video_files = get_video_files()
    
    if not video_files:
        print("  No video/audio files found!")
        sys.exit(0)
    
    print(f"✓ Found {len(video_files)} video/audio files")
    
    # Filter files that need transcription
    files_to_transcribe = []
    large_files_to_transcribe = []
    already_transcribed = []
    
    for video_file in video_files:
        transcript_path = get_transcript_path(video_file)
        
        if transcript_path.exists():
            already_transcribed.append(video_file)
        elif video_file.stat().st_size > MAX_FILE_SIZE:
            large_files_to_transcribe.append(video_file)
        else:
            files_to_transcribe.append(video_file)
    
    print(f"\n  Files to transcribe: {len(files_to_transcribe)}")
    print(f"  Large files to transcribe (will be split): {len(large_files_to_transcribe)}")
    print(f"  Already transcribed: {len(already_transcribed)}")
    
    if not files_to_transcribe and not large_files_to_transcribe:
        print("\n✓ All files already transcribed!")
        return
    
    # Transcribe regular-sized files
    successful = 0
    failed = 0
    
    if files_to_transcribe:
        print(f"\n[3/4] Transcribing {len(files_to_transcribe)} regular-sized files...")
        for i, video_file in enumerate(files_to_transcribe, 1):
            transcript_path = get_transcript_path(video_file)
            
            print(f"\n  [{i}/{len(files_to_transcribe)}] {video_file.name}")
            
            try:
                transcript_text = transcribe_file(client, video_file)
                
                # Save transcript to file
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                
                print(f"    Saved transcript: {transcript_path.name}")
                successful += 1
                
            except ValueError as e:
                print(f"    ✗ Skipped: {e}")
                failed += 1
            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed += 1
    
    # Transcribe large files (with splitting)
    if large_files_to_transcribe:
        print(f"\n[4/4] Transcribing {len(large_files_to_transcribe)} large files (splitting into chunks)...")
        for i, video_file in enumerate(large_files_to_transcribe, 1):
            transcript_path = get_transcript_path(video_file)
            
            print(f"\n  [{i}/{len(large_files_to_transcribe)}] {video_file.name} ({file_size_mb(video_file):.2f}MB)")
            
            try:
                transcript_text = transcribe_large_file(client, video_file)
                
                # Save transcript to file
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                
                print(f"    Saved transcript: {transcript_path.name}")
                successful += 1
                
            except ValueError as e:
                print(f"    ✗ Skipped: {e}")
                failed += 1
            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Transcription Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Already transcribed: {len(already_transcribed)}")
    print("=" * 60)


if __name__ == '__main__':
    main()

