# 📍 Which Shell to Use

## ✅ Correct Shell: `ingest-chromadb` → Shell

**Use the `ingest-chromadb` Background Worker service shell.**

---

## 📋 Step-by-Step Instructions

### Step 1: Go to Render Dashboard
**URL:** https://dashboard.render.com

### Step 2: Find `ingest-chromadb` Service
**Look for:**
- Service name: `ingest-chromadb`
- Type: Background Worker
- Status: Should be "Deployed" or "Live"

### Step 3: Click on `ingest-chromadb`
**Click the service name** to open its details page.

### Step 4: Open Shell
**In the left sidebar:**
- Find **"MANAGE"** section
- Click **"Shell"** (it will be highlighted in purple when active)
- Wait for shell to connect (may show "Reconnecting..." for 10-30 seconds)

### Step 5: Paste Command
**Once shell is connected, paste the command:**

```python
python3 << 'PYEOF'
import urllib.request
import subprocess
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/process_missing_large_files.py'
file_path = '/app/ingestion/process_missing_large_files.py'
urllib.request.urlretrieve(url, file_path)
subprocess.run(['python3', file_path])
PYEOF
```

**Press Enter** to run.

---

## ❌ Don't Use These Shells

### `chromadb` → Shell ❌
- **Why not:** This is the ChromaDB server container
- **Problem:** Doesn't have Python or your files
- **Use for:** ChromaDB server management only

### `chatbot-api` → Shell ❌
- **Why not:** This is the FastAPI web server
- **Problem:** May not have transcript files
- **Use for:** API server management only

### `chromadb-public` → Shell ❌
- **Why not:** This is the public ChromaDB instance
- **Problem:** Doesn't have your files or ingestion scripts
- **Use for:** Public ChromaDB management only

---

## ✅ Why `ingest-chromadb`?

**This service:**
- ✅ Has access to transcript files (`/app/10K2K v2`)
- ✅ Has Python and ingestion scripts
- ✅ Can connect to ChromaDB
- ✅ Designed for ingestion tasks
- ✅ Background Worker (perfect for long-running tasks)

---

## 🔍 How to Identify the Right Service

**Look for:**
- Service name: `ingest-chromadb`
- Type: **Background Worker** (not Web Service)
- Icon: Three horizontal lines (hamburger menu icon)
- Status: "Deployed" or "Live"

**This is the one!**

---

## 📋 Quick Checklist

- [ ] Go to Render Dashboard
- [ ] Find `ingest-chromadb` service
- [ ] Click on it
- [ ] Click "Shell" in left sidebar
- [ ] Wait for connection
- [ ] Paste command
- [ ] Press Enter

---

## ✅ Summary

**Use: `ingest-chromadb` → Shell**

**This is the Background Worker designed for ingestion tasks.**

**It has everything needed: files, Python, scripts, and ChromaDB access.**

