#!/usr/bin/env python3
"""
Live progress monitor for ingestion pipeline
Shows real-time progress bar and status updates
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_total_files():
    """Get total number of transcript files."""
    transcript_dir = Path("10K2K v2")
    if not transcript_dir.exists():
        return 0
    return len(list(transcript_dir.rglob("*.txt")))

def get_processed_count():
    """Get number of processed files from checkpoint."""
    checkpoint_file = Path("checkpoints/ingest_transcripts.json")
    if not checkpoint_file.exists():
        return 0
    try:
        with open(checkpoint_file) as f:
            data = json.load(f)
        return len(data.get("processed", []))
    except:
        return 0

def is_ingestion_running():
    """Check if ingestion container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return "ingest" in result.stdout
    except:
        return False

def get_current_file():
    """Get the current file being processed from logs."""
    log_file = Path("logs/ingest_all.log")
    if not log_file.exists():
        return "Starting..."
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Look for most recent "Processing:" line
            for line in reversed(lines[-50:]):
                if "Processing:" in line:
                    parts = line.split("Processing:")
                    if len(parts) > 1:
                        filename = parts[1].strip().split()[0]
                        return filename
        return "Waiting..."
    except:
        return "Unknown"

def get_recent_status():
    """Get recent status from logs."""
    log_file = Path("logs/ingest_all.log")
    if not log_file.exists():
        return "Initializing..."
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Get last few meaningful lines
            for line in reversed(lines[-10:]):
                if any(keyword in line for keyword in ["✓", "✗", "Progress:", "Summary:"]):
                    # Clean up the line
                    clean_line = line.split(" - ")[-1].strip() if " - " in line else line.strip()
                    return clean_line[:60]  # Truncate if too long
        return "Processing..."
    except:
        return "Unknown"

def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"

def main():
    """Main monitoring loop."""
    print("Starting live progress monitor...")
    print("Press Ctrl+C to exit\n")
    time.sleep(1)
    
    start_time = time.time()
    last_processed = 0
    
    try:
        while True:
            clear_screen()
            
            # Header
            print("╔" + "═" * 58 + "╗")
            print("║" + " " * 15 + "📊 LIVE INGESTION PROGRESS" + " " * 17 + "║")
            print("╚" + "═" * 58 + "╝")
            print()
            
            # Get data
            total = get_total_files()
            processed = get_processed_count()
            remaining = total - processed
            running = is_ingestion_running()
            current_file = get_current_file()
            recent_status = get_recent_status()
            
            # Status indicator
            status_icon = "🟢" if running else "🔴"
            status_text = "RUNNING" if running else "STOPPED"
            print(f"Status: {status_icon} {status_text}")
            print()
            print("─" * 60)
            print()
            
            # Progress info
            if total > 0:
                percentage = (processed / total) * 100
            else:
                percentage = 0
            
            print(f"{'Total files:':<25} {total}")
            print(f"{'✅ Processed:':<25} \033[92m{processed}\033[0m")
            print(f"{'⏳ Remaining:':<25} \033[93m{remaining}\033[0m")
            print()
            
            # Progress bar
            bar_length = 50
            filled = int((percentage / 100) * bar_length)
            empty = bar_length - filled
            
            bar = "\033[92m" + "█" * filled + "\033[93m" + "░" * empty + "\033[0m"
            print(f"Progress: [{bar}] {percentage:.1f}%")
            print()
            print("─" * 60)
            print()
            
            # Current activity
            print(f"Current file: \033[94m{current_file}\033[0m")
            print(f"Status:        {recent_status}")
            print()
            
            # Processing rate
            elapsed = time.time() - start_time
            if processed > last_processed and elapsed > 0:
                rate = (processed - last_processed) / elapsed if elapsed > 0 else 0
                if rate > 0:
                    print(f"Processing rate: {rate:.2f} files/second")
                    if remaining > 0 and rate > 0:
                        eta_seconds = remaining / rate
                        print(f"⏱️  Estimated time remaining: {format_time(int(eta_seconds))}")
                last_processed = processed
                start_time = time.time()
            
            print()
            print("─" * 60)
            print()
            print(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            print("Press Ctrl+C to exit")
            
            # Update every 2 seconds
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
        print("To restart monitoring, run: python3 monitor_progress.py")

if __name__ == "__main__":
    main()

