# 🔧 Alternative Methods: Shell Keeps Disconnecting

## ⚠️ Problem: Shell Keeps Reconnecting

The Render Shell keeps disconnecting while you try to type, making it impossible to upload the script manually.

**This is happening because:**
- Service keeps restarting due to OOM errors
- Each restart disconnects the Shell
- Can't type long commands before it reconnects

---

## ✅ Solution 1: Wait for Service to Stabilize

**Before using Shell:**
1. **Stop the current ingestion process** (if running)
2. **Wait for service to stabilize** (no more OOM errors)
3. **Then use Shell** when service is stable

**How to check if stable:**
- Go to **Events tab**
- Look for "Service recovered" messages
- Wait until no new failures for 2-3 minutes
- Then try Shell again

---

## ✅ Solution 2: Use Python One-Liner (Easiest)

**Instead of uploading the file, create it directly with Python:**

**In Render Shell, run this ONE command:**

```python
python3 << 'PYEOF'
import os
script_content = '''#!/usr/bin/env python3
"""
Standalone Recursive File Splitting & Cloud Ingestion
"""
import os, sys, re, subprocess, time, shutil
from pathlib import Path
from typing import List, Optional

CHROMA_HOST = os.getenv('CHROMA_HOST', 'chromadb-w5jr')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')
TRANSCRIPTS_DIR = Path(os.getenv('TRANSCRIPTS_DIR', '/app/10K2K v2'))
INGEST_SCRIPT = Path('/app/ingestion/ingest_single_transcript_ultra_minimal.py')
PYTHON_CMD = 'python3'
MAX_INITIAL_SIZE_MB = 5.0
MIN_SEGMENT_SIZE_KB = 100.0
MAX_RECURSION_DEPTH = 5
RETRY_DELAY_SECONDS = 2.0
MAX_RETRIES = 3

stats = {'files_processed': 0, 'files_split': 0, 'segments_created': 0, 'recursion_levels': {}, 'files_failed': []}

def split_at_semantic_boundaries(content: str, target_size_bytes: int) -> List[str]:
    segments = []
    paragraphs = content.split('\\n\\n')
    current_segment = ""
    current_size = 0
    for para in paragraphs:
        para_size = len(para.encode('utf-8'))
        if para_size > target_size_bytes:
            lines = para.split('\\n')
            for line in lines:
                line_size = len(line.encode('utf-8'))
                if line_size > target_size_bytes:
                    sentences = re.split(r'(?<=[.!?])\\s+', line)
                    for sentence in sentences:
                        sent_size = len(sentence.encode('utf-8'))
                        if sent_size > target_size_bytes:
                            clauses = re.split(r'(?<=[,;:])\\s+', sentence)
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
                        current_segment += ("\\n" + line if current_segment else line)
                        current_size += line_size
        else:
            if current_size + para_size > target_size_bytes and current_segment:
                segments.append(current_segment.strip())
                current_segment = para
                current_size = para_size
            else:
                current_segment += ("\\n\\n" + para if current_segment else para)
                current_size += para_size
    if current_segment.strip():
        segments.append(current_segment.strip())
    return segments

def create_segment_file(original_file: Path, segment_num: int, content: str, temp_dir: Path) -> Path:
    base_name = original_file.stem
    extension = original_file.suffix
    segment_name = f"{base_name}_{segment_num:02d}{extension}"
    segment_path = temp_dir / segment_name
    with open(segment_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return segment_path

def ingest_file_segment(segment_path: Path, retry_count: int = 0) -> bool:
    if retry_count >= MAX_RETRIES:
        print(f"✗ Max retries ({MAX_RETRIES}) exceeded for {segment_path.name}")
        return False
    try:
        print(f"  Ingesting segment: {segment_path.name} (attempt {retry_count + 1}/{MAX_RETRIES})")
        result = subprocess.run([PYTHON_CMD, str(INGEST_SCRIPT), str(segment_path)], capture_output=True, text=True, timeout=1800)
        if result.returncode == 0:
            print(f"  ✓ Successfully ingested: {segment_path.name}")
            return True
        else:
            print(f"  ⚠️  Ingestion failed (exit {result.returncode}): {segment_path.name}")
            time.sleep(RETRY_DELAY_SECONDS * (2 ** retry_count))
            return ingest_file_segment(segment_path, retry_count + 1)
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timeout ingesting: {segment_path.name}")
        time.sleep(RETRY_DELAY_SECONDS * (2 ** retry_count))
        return ingest_file_segment(segment_path, retry_count + 1)
    except Exception as e:
        print(f"  ✗ Error ingesting {segment_path.name}: {e}")
        return False

def process_file_recursive(file_path: Path, recursion_level: int = 0, temp_dir: Optional[Path] = None) -> bool:
    if recursion_level >= MAX_RECURSION_DEPTH:
        print(f"✗ Max recursion depth ({MAX_RECURSION_DEPTH}) reached for {file_path.name}")
        stats['files_failed'].append(str(file_path))
        return False
    if recursion_level not in stats['recursion_levels']:
        stats['recursion_levels'][recursion_level] = 0
    stats['recursion_levels'][recursion_level] += 1
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    indent = "  " * recursion_level
    print(f"{indent}Processing: {file_path.name} ({file_size_mb:.2f}MB, level {recursion_level})")
    if file_size_mb <= MAX_INITIAL_SIZE_MB:
        print(f"{indent}Attempting to ingest as-is...")
        if ingest_file_segment(file_path):
            print(f"{indent}✓ Successfully ingested: {file_path.name}")
            stats['files_processed'] += 1
            return True
        else:
            print(f"{indent}⚠️  Ingestion failed, will split: {file_path.name}")
    print(f"{indent}Splitting file: {file_path.name}")
    if temp_dir is None:
        temp_dir = file_path.parent / f".segments_{file_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"{indent}✗ Failed to read file {file_path.name}: {e}")
        stats['files_failed'].append(str(file_path))
        return False
    target_size_bytes = max(int(len(content.encode('utf-8')) / 2), int(MIN_SEGMENT_SIZE_KB * 1024))
    segments = split_at_semantic_boundaries(content, target_size_bytes)
    print(f"{indent}Split into {len(segments)} segments")
    if len(segments) == 1:
        print(f"{indent}⚠️  Could not split further, attempting ingestion...")
        if ingest_file_segment(file_path):
            print(f"{indent}✓ Successfully ingested unsplit: {file_path.name}")
            stats['files_processed'] += 1
            return True
        else:
            print(f"{indent}✗ Failed to ingest unsplit file: {file_path.name}")
            stats['files_failed'].append(str(file_path))
            return False
    segment_files = []
    for i, segment_content in enumerate(segments, 1):
        segment_file = create_segment_file(file_path, i, segment_content, temp_dir)
        segment_files.append(segment_file)
        stats['segments_created'] += 1
    all_succeeded = True
    for segment_file in segment_files:
        if not process_file_recursive(segment_file, recursion_level + 1, temp_dir):
            all_succeeded = False
    if all_succeeded:
        print(f"{indent}✓ All segments succeeded for: {file_path.name}")
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"{indent}⚠️  Could not cleanup temp directory: {e}")
        stats['files_split'] += 1
        return True
    else:
        print(f"{indent}✗ Some segments failed for: {file_path.name}")
        stats['files_failed'].append(str(file_path))
        return False

def find_large_files() -> List[Path]:
    print(f"Scanning for files larger than {MAX_INITIAL_SIZE_MB}MB...")
    large_files = []
    if not TRANSCRIPTS_DIR.exists():
        print(f"✗ Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
        return large_files
    for txt_file in TRANSCRIPTS_DIR.rglob('*.txt'):
        if txt_file.is_file():
            try:
                file_size_mb = txt_file.stat().st_size / (1024 * 1024)
                if file_size_mb > MAX_INITIAL_SIZE_MB:
                    large_files.append(txt_file)
                    print(f"  Found large file: {txt_file.name} ({file_size_mb:.2f}MB)")
            except Exception as e:
                print(f"  ⚠️  Error checking {txt_file.name}: {e}")
    print(f"\\nFound {len(large_files)} files larger than {MAX_INITIAL_SIZE_MB}MB")
    return large_files

def main():
    print("=" * 70)
    print("RECURSIVE FILE SPLITTING & CLOUD INGESTION")
    print("=" * 70)
    print(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Max file size (as-is): {MAX_INITIAL_SIZE_MB}MB")
    print("=" * 70)
    large_files = find_large_files()
    if not large_files:
        print("\\n✅ No large files found. All files are within size limits!")
        return 0
    print(f"\\nProcessing {len(large_files)} large files...")
    print("=" * 70)
    for i, file_path in enumerate(large_files, 1):
        print(f"\\n[{i}/{len(large_files)}] Processing: {file_path.name}")
        print("-" * 70)
        process_file_recursive(file_path)
    print("\\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files split: {stats['files_split']}")
    print(f"Total segments created: {stats['segments_created']}")
    print(f"Recursion levels used:")
    for level, count in sorted(stats['recursion_levels'].items()):
        print(f"  Level {level}: {count} files")
    if stats['files_failed']:
        print(f"\\n⚠️  {len(stats['files_failed'])} files failed:")
        for failed_file in stats['files_failed']:
            print(f"  - {failed_file}")
    else:
        print("\\n✅ All files successfully ingested!")
    print("=" * 70)
    return 0 if not stats['files_failed'] else 1

if __name__ == "__main__":
    sys.exit(main())
'''

with open('/app/ingestion/ingest_with_recursive_splitting_standalone.py', 'w') as f:
    f.write(script_content)
print("✅ Script created successfully!")
print("Run: python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py")
PYEOF
```

**This creates the file in ONE command - no typing needed!**

---

## ✅ Solution 3: Use Logs Tab Instead

**Instead of Shell, you can run commands via environment variables:**

1. **Go to Render → `ingest-chromadb` → Environment**
2. **Add environment variable:**
   - Key: `RUN_RECURSIVE_SPLIT`
   - Value: `true`
3. **Modify the startup command** to check this variable and run the script

**Or modify the Dockerfile CMD** to run the script automatically.

---

## ✅ Solution 4: Stop Current Process First

**The service might be crashing because ingestion is already running:**

1. **Check Logs tab** - is ingestion currently running?
2. **If yes, stop it** (service restart will stop it)
3. **Wait for service to stabilize**
4. **Then use Shell** when stable

---

## ✅ Solution 5: Use GitHub + Manual Deploy

**Instead of Shell:**

1. **Commit the standalone script to GitHub**
2. **Push to GitHub**
3. **Go to Render → `ingest-chromadb` → Manual Deploy**
4. **Deploy latest commit**
5. **Wait for deployment**
6. **Then run script** (file will be there)

---

## 🎯 Recommended Approach

**Best solution: Use Solution 2 (Python One-Liner)**

**Why:**
- ✅ Single command (copy-paste)
- ✅ No typing needed
- ✅ Works even if Shell disconnects
- ✅ Creates file immediately

**Steps:**
1. Wait for Shell to connect (even if briefly)
2. Copy the Python one-liner from Solution 2
3. Paste it all at once
4. Press Enter
5. File is created!

---

## 📋 Summary

**If Shell keeps disconnecting:**
1. **Try Solution 2** (Python one-liner) - easiest
2. **Or wait for service to stabilize** first
3. **Or use GitHub + Manual Deploy** (permanent solution)

**The Python one-liner creates the file in one command - no typing needed!**

