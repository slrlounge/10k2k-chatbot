# 📁 Local File Splitting & Ingestion Instructions

## Overview

This guide walks you through:
1. **Splitting files locally** into 0.01MB (10KB) segments
2. **Ingesting the pre-split files** into ChromaDB on Render

---

## Step 1: Split Files Locally

### Run the Splitting Script

```bash
python3 split_files_locally.py
```

### What It Does

- ✅ Scans all `.txt` files in `10K2K v2/` directory
- ✅ Splits files larger than 0.01MB (10KB) into smaller segments
- ✅ Names segments logically: `sales_01.txt`, `sales_02.txt`, etc.
- ✅ Backs up original files to `10K2K v2_backup/` directory
- ✅ Keeps files organized in their original directories

### Example Output

```
[1/161] 13_STEP THIRTEEN/s13-06-asking-right-questions.txt
  📄 Processing: s13-06-asking-right-questions.txt (0.019MB)
     → Splitting into 3 segments...
     → Original backed up to: 10K2K v2_backup/13_STEP THIRTEEN/s13-06-asking-right-questions.txt
     ✓ Created 3 segments
```

### File Naming Convention

- **Original:** `sales.txt` (20KB)
- **Segments:** 
  - `sales_01.txt` (10KB)
  - `sales_02.txt` (10KB)

- **Original:** `00-S13-ALL-IN-ONE.txt` (80KB)
- **Segments:**
  - `00-S13-ALL-IN-ONE_01.txt` (~10KB)
  - `00-S13-ALL-IN-ONE_02.txt` (~10KB)
  - `00-S13-ALL-IN-ONE_03.txt` (~10KB)
  - ... (up to 9 segments)

---

## Step 2: Verify Splitting Results

### Check Summary

After splitting completes, you'll see a summary:

```
SPLITTING SUMMARY
======================================================================
Files processed: 161
Files split: 45
Files skipped (already small): 116
Total segments created: 234
Original total size: 12.34MB
Segments total size: 12.45MB
```

### Verify Files

```bash
# Count original files (backed up)
ls -R "10K2K v2_backup" | grep "\.txt$" | wc -l

# Count split files (in main directory)
find "10K2K v2" -name "*.txt" | wc -l
```

---

## Step 3: Commit and Push Split Files

### Add Split Files to Git

```bash
git add "10K2K v2/"
git commit -m "Split large transcript files into 0.01MB segments"
git push
```

**Important:** Make sure to commit the split files so they're available in Render!

---

## Step 4: Deploy to Render

Wait for Render to auto-deploy, or manually trigger deployment.

---

## Step 5: Ingest Pre-Split Files in Render

### Connect to Render Shell

1. Go to Render Dashboard
2. Click on `ingest-chromadb` service
3. Click "Shell" in left sidebar
4. Wait for shell to connect

### Run Ingestion Script

**Option 1: Download and Run**

```python
python3 << 'PYEOF'
import urllib.request
import subprocess
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_pre_split_files.py'
file_path = '/app/ingestion/ingest_pre_split_files.py'
urllib.request.urlretrieve(url, file_path)
subprocess.run(['python3', file_path])
PYEOF
```

**Option 2: If Already Deployed**

```bash
python3 /app/ingestion/ingest_pre_split_files.py
```

### What It Does

- ✅ Finds all `.txt` files (including segments) in `/app/10K2K v2/`
- ✅ Ingests each file sequentially using `ingest_single_transcript_ultra_minimal.py`
- ✅ Processes files in logical order (by directory and filename)
- ✅ Shows progress for each file
- ✅ Provides summary at the end

### Expected Output

```
[1/234] 13_STEP THIRTEEN/s13-06-asking-right-questions_01.txt
  ✓ Successfully ingested

[2/234] 13_STEP THIRTEEN/s13-06-asking-right-questions_02.txt
  ✓ Successfully ingested

...

INGESTION SUMMARY
======================================================================
Files found: 234
Files processed: 234
Files succeeded: 234
Files failed: 0

✅ All files successfully ingested!
```

---

## Troubleshooting

### Files Not Found in Render

If files aren't found in Render, make sure:
1. ✅ Files are committed to Git
2. ✅ Render has auto-deployed (check deployment logs)
3. ✅ Files are in `10K2K v2/` directory (not `10K2K v2_backup/`)

### Ingestion Failures

If some files fail to ingest:
- Check Render logs for errors
- Verify ChromaDB connection
- Ensure files are ≤0.01MB (should be after splitting)

### Restore Original Files

If you need to restore original files:

```bash
# Restore from backup
cp -r "10K2K v2_backup/"* "10K2K v2/"
```

---

## Summary

1. ✅ **Split locally:** `python3 split_files_locally.py`
2. ✅ **Commit & push:** `git add "10K2K v2/" && git commit -m "Split files" && git push`
3. ✅ **Wait for Render deploy**
4. ✅ **Ingest in Render Shell:** Run `ingest_pre_split_files.py`

All files will be split into 0.01MB segments and ingested successfully! 🎉

