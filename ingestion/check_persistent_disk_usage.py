#!/usr/bin/env python3
"""
Check if ChromaDB is writing to the persistent disk.
Run this in chromadb service Shell to verify data is being stored.
"""

import os
import subprocess
from pathlib import Path

PERSIST_DIR = Path("/chroma/chroma")

def run_command(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return f"Error: {e}", 1

def main():
    print("=" * 70)
    print("PERSISTENT DISK USAGE CHECK")
    print("=" * 70)
    print()
    print("Checking if ChromaDB is storing data on persistent disk...")
    print()
    
    # Step 1: Check disk mount
    print("Step 1: Checking disk mount...")
    output, code = run_command("df -h /chroma/chroma")
    if code == 0:
        print(f"  {output}")
        lines = output.split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                size = parts[1]
                used = parts[2]
                avail = parts[3]
                use_pct = parts[4]
                print(f"\n  Disk Status:")
                print(f"    Size: {size}")
                print(f"    Used: {used}")
                print(f"    Available: {avail}")
                print(f"    Usage: {use_pct}")
                
                # Check if disk is being used
                if used != "28K" and used != "0":
                    print(f"\n  ✓ Disk is being used! ({used} used)")
                else:
                    print(f"\n  ⚠️  Disk is empty or barely used ({used})")
                    print(f"     This suggests ChromaDB is NOT writing to persistent disk")
    else:
        print(f"  ✗ Error checking disk: {output}")
    
    print()
    
    # Step 2: List files on persistent disk
    print("Step 2: Listing files on persistent disk...")
    if PERSIST_DIR.exists():
        output, code = run_command(f"ls -lah {PERSIST_DIR}")
        if code == 0:
            print(f"  {output}")
            
            # Count files (excluding . and ..)
            files = [f for f in PERSIST_DIR.iterdir() if f.name not in ['.', '..']]
            if files:
                print(f"\n  ✓ Found {len(files)} file(s)/directory(ies) on persistent disk:")
                for f in files[:10]:  # Show first 10
                    size = f.stat().st_size if f.exists() else 0
                    print(f"    - {f.name} ({size:,} bytes)")
                if len(files) > 10:
                    print(f"    ... and {len(files) - 10} more")
            else:
                print(f"\n  ⚠️  Persistent disk is empty (only . and ..)")
                print(f"     ChromaDB is NOT storing data here")
        else:
            print(f"  ✗ Error listing files: {output}")
    else:
        print(f"  ✗ Directory {PERSIST_DIR} does not exist!")
    
    print()
    
    # Step 3: Check ChromaDB process and environment
    print("Step 3: Checking ChromaDB environment variables...")
    env_vars = ["IS_PERSISTENT", "PERSIST_DIRECTORY"]
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        print(f"  {var}: {value}")
    
    print()
    
    # Step 4: Check disk usage over time
    print("Step 4: Checking disk usage details...")
    output, code = run_command(f"du -sh {PERSIST_DIR}/* 2>/dev/null | head -20")
    if code == 0 and output:
        print(f"  {output}")
    else:
        print(f"  No files found or error checking disk usage")
    
    print()
    
    # Step 5: Check if ChromaDB process is running
    print("Step 5: Checking ChromaDB process...")
    output, code = run_command("ps aux | grep -i chroma | grep -v grep")
    if code == 0 and output:
        print(f"  ChromaDB process found:")
        print(f"  {output}")
    else:
        print(f"  ⚠️  ChromaDB process not found (or error checking)")
    
    print()
    print("=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    print()
    
    # Final assessment
    if PERSIST_DIR.exists():
        files = [f for f in PERSIST_DIR.iterdir() if f.name not in ['.', '..']]
        output, code = run_command("df -h /chroma/chroma")
        if code == 0 and len(output.split('\n')) > 1:
            parts = output.split('\n')[1].split()
            if len(parts) >= 3:
                used = parts[2]
                
                if files and used != "28K" and used != "0":
                    print("✓ ChromaDB IS writing to persistent disk")
                    print(f"  Found {len(files)} files, {used} disk space used")
                else:
                    print("⚠️  ChromaDB is NOT writing to persistent disk")
                    print("  Possible causes:")
                    print("    1. ChromaDB wasn't redeployed after adding persistent disk")
                    print("    2. Environment variables not set correctly")
                    print("    3. ChromaDB is using a different directory")
                    print()
                    print("  Solution:")
                    print("    1. Redeploy ChromaDB service")
                    print("    2. Verify IS_PERSISTENT=TRUE and PERSIST_DIRECTORY=/chroma/chroma")
                    print("    3. Check ChromaDB logs for errors")
    
    print()
    return 0

if __name__ == "__main__":
    exit(main())

