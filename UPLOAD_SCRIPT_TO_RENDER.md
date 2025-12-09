# 🚀 Upload Script Directly to Render Shell

## ⚠️ Problem: Service Crashing Due to Large Files

The service is running out of memory because it's trying to ingest files that are too large. The recursive splitting script will solve this, but it needs to be deployed first.

---

## ✅ Solution: Upload Script Directly

Since deployment keeps failing due to OOM errors, upload the script directly to Render Shell.

---

## 📋 Step-by-Step Instructions

### Step 1: Open Render Shell

**Render → `ingest-chromadb` → Shell**

Wait for shell to connect.

---

### Step 2: Create the Script File

**Run this command in Shell:**

```bash
cat > /app/ingestion/ingest_with_recursive_splitting_standalone.py << 'ENDOFFILE'
```

**Press Enter** (don't type ENDOFFILE yet)

---

### Step 3: Copy Script Content

**I'll provide the script content below - copy the ENTIRE content:**

[The script content is in `ingestion/ingest_with_recursive_splitting_standalone.py`]

**Copy everything from `#!/usr/bin/env python3` to the last line.**

---

### Step 4: Paste and Save

1. **Paste the entire script** into the Shell
2. **Press Enter**
3. **Type:** `ENDOFFILE`
4. **Press Enter** to save

---

### Step 5: Make Executable

```bash
chmod +x /app/ingestion/ingest_with_recursive_splitting_standalone.py
```

---

### Step 6: Run the Script

```bash
python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py
```

---

## 🎯 What This Script Does

1. **Finds large files** (>5MB) that are causing OOM errors
2. **Splits them** at semantic boundaries (paragraphs, sentences)
3. **Ingests each segment** using the ultra-minimal script
4. **Recursively retries** if segments still fail
5. **Continues until all segments succeed**

---

## ⚙️ Configuration

**The script uses these settings:**
- `MAX_INITIAL_SIZE_MB = 5.0` - Try files up to 5MB as-is
- `MIN_SEGMENT_SIZE_KB = 100.0` - Minimum 100KB per segment
- `MAX_RECURSION_DEPTH = 5` - Max 5 levels of splitting

**These are conservative to avoid memory issues.**

---

## 📊 Expected Output

```
======================================================================
RECURSIVE FILE SPLITTING & CLOUD INGESTION
======================================================================
ChromaDB: chromadb-w5jr:8000
Collection: 10k2k_transcripts
Max file size (as-is): 5.0MB
======================================================================
Scanning for files larger than 5.0MB...
  Found large file: filename.txt (15.2MB)

Found 1 files larger than 5.0MB

Processing 1 large files...
======================================================================

[1/1] Processing: filename.txt
----------------------------------------------------------------------
Processing: filename.txt (15.2MB, level 0)
Splitting file: filename.txt
Split into 3 segments
  Processing: filename_01.txt (5.1MB, level 1)
  Ingesting segment: filename_01.txt (attempt 1/3)
  ✓ Successfully ingested: filename_01.txt
  ...
```

---

## ⚠️ Important Notes

### Memory Management
- Script processes files one at a time
- Each segment is ingested separately
- Memory is released between segments
- Should avoid OOM errors

### File Persistence
- **This upload is temporary** - file will be lost on next deployment
- For permanent solution, wait for GitHub deployment to complete
- Or commit and push the standalone version

---

## 🔧 Alternative: Quick One-Liner Upload

**If the above is too complex, use this one-liner:**

```bash
curl -o /app/ingestion/ingest_with_recursive_splitting_standalone.py https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py
```

**Then run:**
```bash
python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py
```

---

## ✅ Summary

**The script will:**
1. Find all files >5MB
2. Split them recursively
3. Ingest each segment
4. Prevent OOM errors

**Upload it directly to Render Shell and run it!**

