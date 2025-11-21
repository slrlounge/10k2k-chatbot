# 🔄 Recursive File Splitting & Cloud Ingestion Guide

## 📋 Overview

This script automatically identifies failed files and recursively splits them until all segments successfully ingest into ChromaDB.

**Key Features:**
- ✅ Identifies failed files from checkpoints
- ✅ Splits files at semantic boundaries (paragraphs, sentences, line breaks)
- ✅ Recursively retries until all segments succeed
- ✅ Proper naming conventions (`filename_01.txt`, `filename_02.txt`)
- ✅ Verifies segments are actually stored in ChromaDB
- ✅ Comprehensive reporting

---

## 🚀 Quick Start

### Option 1: Run Locally (for testing)

```bash
cd /Users/justinlin/Documents/10K2KChatBot
python3 ingestion/ingest_with_recursive_splitting.py
```

### Option 2: Run in Render Shell (for production)

**Render → `ingest-chromadb` → Shell**

```bash
python3 /app/ingestion/ingest_with_recursive_splitting.py
```

---

## ⚙️ Configuration

### Environment Variables

Set these in your `.env` file or Render environment:

```bash
# ChromaDB Connection
CHROMA_HOST=chromadb-w5jr
CHROMA_PORT=8000
COLLECTION_NAME=10k2k_transcripts

# File Paths
TRANSCRIPTS_DIR=/app/10K2K v2

# Ingestion Script
INGEST_SCRIPT_ULTRA_MINIMAL=/app/ingestion/ingest_single_transcript_ultra_minimal.py
PYTHON_CMD=python3

# Splitting Configuration
MAX_INITIAL_SIZE_MB=10.0          # Try to ingest files up to 10MB as-is
MIN_SEGMENT_SIZE_KB=50.0         # Minimum 50KB per segment
MAX_RECURSION_DEPTH=5            # Max 5 levels of splitting
RETRY_DELAY_SECONDS=2.0          # Base delay between retries
MAX_RETRIES=3                    # Max retries per segment
```

---

## 🔍 How It Works

### Step 1: Identify Failed Files

The script:
1. Scans `TRANSCRIPTS_DIR` for all `.txt` files
2. Checks checkpoint for processed files
3. Identifies files NOT in processed set
4. These are the "failed" files to process

### Step 2: Attempt Direct Ingestion

For each failed file:
1. Try to ingest as-is (if under `MAX_INITIAL_SIZE_MB`)
2. If successful → Done! ✅
3. If failed → Proceed to splitting

### Step 3: Recursive Splitting

If ingestion fails:
1. **Split at semantic boundaries:**
   - First: Try paragraphs (double newlines)
   - Then: Try sentences (`.`, `!`, `?`)
   - Then: Try clauses (`,`, `;`, `:`)
   - Never splits words

2. **Create segment files:**
   - `originalname_01.txt`
   - `originalname_02.txt`
   - `originalname_03.txt`
   - etc.

3. **Process each segment recursively:**
   - If segment succeeds → Done! ✅
   - If segment fails → Split it further
   - Continue until all segments succeed

### Step 4: Verification

After each segment ingestion:
1. Verify segment is actually in ChromaDB
2. If not found → Retry with exponential backoff
3. Continue until verified

### Step 5: Cleanup

When all segments succeed:
1. Delete temporary segment files
2. Mark original file as processed
3. Report success

---

## 📊 Example Output

```
======================================================================
RECURSIVE FILE SPLITTING & CLOUD INGESTION
======================================================================
Identifying failed files...
Found 159 total transcript files
Found 12 processed files in checkpoint
Identified 147 failed/unprocessed files

Processing 147 failed files...
======================================================================

[1/147] Processing: large-file.txt
----------------------------------------------------------------------
Processing: large-file.txt (15.2MB, level 0)
Splitting file: large-file.txt
Split into 3 segments
  Processing: large-file_01.txt (5.1MB, level 1)
  ✓ Successfully ingested: large-file_01.txt
  Processing: large-file_02.txt (5.0MB, level 1)
  ✓ Successfully ingested: large-file_02.txt
  Processing: large-file_03.txt (5.1MB, level 1)
  ✓ Successfully ingested: large-file_03.txt
✓ All segments succeeded for: large-file.txt

======================================================================
INGESTION SUMMARY
======================================================================
Files processed: 145
Files split: 2
Total segments created: 6
Recursion levels used:
  Level 0: 147 files
  Level 1: 2 files

✅ All files successfully ingested!
======================================================================
```

---

## 🎯 Naming Conventions

### Original Files
- `sales.txt`
- `step3_brand_experience.txt`
- `00-S1-ALL-IN-ONE.txt`

### Split Segments
- `sales_01.txt`, `sales_02.txt`, `sales_03.txt`
- `step3_brand_experience_01.txt`, `step3_brand_experience_02.txt`
- `00-S1-ALL-IN-ONE_01.txt`, `00-S1-ALL-IN-ONE_02.txt`

**Rules:**
- Zero-padded numbers (`01`, `02`, `03`, not `1`, `2`, `3`)
- Preserves original base filename
- Maintains semantic grouping
- Preserves ordering for retrieval

---

## 🔧 Troubleshooting

### Issue: Script hangs or times out

**Solution:**
- Increase timeout in `ingest_file_segment()` function
- Check ChromaDB connection
- Verify network connectivity

### Issue: Segments still too large

**Solution:**
- Reduce `MAX_INITIAL_SIZE_MB`
- Reduce `MIN_SEGMENT_SIZE_KB`
- Increase `MAX_RECURSION_DEPTH`

### Issue: Segments not found in ChromaDB

**Solution:**
- Check ChromaDB connection (`CHROMA_HOST`, `CHROMA_PORT`)
- Verify collection name (`COLLECTION_NAME`)
- Check ingestion script logs for errors

### Issue: Too many recursion levels

**Solution:**
- Increase `MAX_RECURSION_DEPTH`
- Reduce `MIN_SEGMENT_SIZE_KB`
- Check if file has semantic boundaries (may need manual splitting)

---

## 📈 Performance Tips

1. **Start with smaller files:** Process smallest files first
2. **Monitor recursion depth:** High depth = very small segments
3. **Check ChromaDB:** Verify segments are actually stored
4. **Use appropriate sizes:** Balance between too many segments and too large files

---

## ✅ Safety Features

- ✅ Never splits words or mid-sentence
- ✅ Preserves semantic meaning
- ✅ Verifies segments in ChromaDB before marking success
- ✅ Exponential backoff for retries
- ✅ Maximum recursion depth to prevent infinite loops
- ✅ Comprehensive error handling
- ✅ Detailed logging

---

## 📋 Summary

**This script ensures:**
- ✅ Every file is successfully ingested
- ✅ No ingestion fails due to file size
- ✅ Files are split at semantic boundaries
- ✅ All segments are verified in ChromaDB
- ✅ Proper naming conventions are maintained
- ✅ Comprehensive reporting is provided

**Run it and let it handle all failed files automatically!**

