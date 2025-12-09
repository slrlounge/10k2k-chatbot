# 🔧 Fix: curl Command Not Found

## ⚠️ Problem
`curl` is not installed in the Render container, so the download command fails.

---

## ✅ Solution: Use Python Instead

**Python is available, so use it to download the script:**

**In Render Shell, run this ONE command:**

```python
python3 << 'PYEOF'
import urllib.request
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py'
file_path = '/app/ingestion/ingest_with_recursive_splitting_standalone.py'
urllib.request.urlretrieve(url, file_path)
print(f"✅ Script downloaded to {file_path}")
print("Run: python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py")
PYEOF
```

**Then run the script:**

```bash
python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py
```

---

## ✅ Or Combine Into One Command

**Download and run in one go:**

```python
python3 << 'PYEOF'
import urllib.request
import subprocess
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py'
file_path = '/app/ingestion/ingest_with_recursive_splitting_standalone.py'
print("Downloading script...")
urllib.request.urlretrieve(url, file_path)
print(f"✅ Script downloaded to {file_path}")
print("Running script...")
subprocess.run(['python3', file_path])
PYEOF
```

---

## ✅ Alternative: Use wget (if available)

**Some containers have `wget` instead of `curl`:**

```bash
wget -O /app/ingestion/ingest_with_recursive_splitting_standalone.py https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py
```

**Then run:**

```bash
python3 /app/ingestion/ingest_with_recursive_splitting_standalone.py
```

---

## 📋 Summary

**Since `curl` is not available, use Python instead:**

1. **Copy the Python download command** above
2. **Paste into Shell**
3. **Press Enter**
4. **Script downloads and can be run**

**Python's `urllib` is built-in, so it will always work!**

