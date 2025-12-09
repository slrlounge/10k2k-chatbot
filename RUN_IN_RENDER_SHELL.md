# 🚀 How to Run Recursive Splitting Script in Render Shell

## 📋 Step-by-Step Instructions

### Step 1: Open Render Shell

1. Go to **Render Dashboard**: https://dashboard.render.com
2. Click on **`ingest-chromadb`** service (Background Worker)
3. Click **"Shell"** in the left sidebar (under MANAGE section)
4. Wait for shell to connect (may show "Reconnecting..." for 10-30 seconds)

---

### Step 2: Copy and Paste This Command

**Once the shell is connected, copy and paste this entire command:**

```bash
python3 /app/ingestion/ingest_with_recursive_splitting.py
```

**Press Enter** to run it.

---

### Step 3: Monitor Progress

**The script will:**
1. Identify failed files
2. Process each file (splitting if needed)
3. Show progress for each file
4. Display final summary

**You'll see output like:**
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

[1/147] Processing: filename.txt
----------------------------------------------------------------------
Processing: filename.txt (5.2MB, level 0)
✓ Successfully ingested: filename.txt
...
```

---

## ⚠️ Important Notes

### Script May Take Time
- **Processing 147 files** can take **30-60 minutes** or more
- Each file may need splitting and multiple retries
- **Don't close the browser tab** while it's running

### If Shell Disconnects
- Script will continue running in background
- Check **Logs tab** for progress
- You can reconnect Shell to see output

### To Stop Script
- Press **Ctrl+C** in Shell
- Script will stop gracefully
- Already processed files will be saved in checkpoint

---

## 🔍 Alternative: Check Progress in Logs

**If Shell disconnects, check Logs:**

**Render → `ingest-chromadb` → Logs**

**Look for:**
- "Processing: [filename]"
- "✓ Successfully ingested"
- "INGESTION SUMMARY"

---

## 📊 Expected Output

**When complete, you'll see:**

```
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

## 🆘 Troubleshooting

### Issue: "python3: command not found"

**Solution:** Use `python` instead:
```bash
python /app/ingestion/ingest_with_recursive_splitting.py
```

### Issue: "No such file or directory"

**Solution:** Check script exists:
```bash
ls -la /app/ingestion/ingest_with_recursive_splitting.py
```

### Issue: Script hangs

**Solution:** 
- Check ChromaDB connection
- Check Logs tab for errors
- Verify environment variables are set

---

## ✅ Quick Command Reference

**Run script:**
```bash
python3 /app/ingestion/ingest_with_recursive_splitting.py
```

**Check if script exists:**
```bash
ls -la /app/ingestion/ingest_with_recursive_splitting.py
```

**Check environment variables:**
```bash
echo $CHROMA_HOST
echo $CHROMA_PORT
echo $TRANSCRIPTS_DIR
```

**Check ChromaDB connection:**
```bash
python3 << 'EOF'
import chromadb
client = chromadb.HttpClient(host='chromadb-w5jr', port=8000)
print(client.heartbeat())
EOF
```

---

## 📋 Summary

1. **Go to Render → `ingest-chromadb` → Shell**
2. **Wait for connection** (10-30 seconds)
3. **Paste:** `python3 /app/ingestion/ingest_with_recursive_splitting.py`
4. **Press Enter**
5. **Monitor progress** (may take 30-60 minutes)
6. **Check summary** at the end

**That's it! The script will handle everything automatically.**

