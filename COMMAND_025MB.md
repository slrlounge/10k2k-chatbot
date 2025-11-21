# 📋 Copy-Paste Command: 0.25MB Threshold

## ✅ Ready-to-Use Command

**Copy this entire command and paste into Render Shell:**

```python
python3 << 'PYEOF'
import urllib.request
import subprocess
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py'
file_path = '/app/ingestion/ingest_with_recursive_splitting_standalone.py'
print('Downloading script (0.25MB threshold)...')
urllib.request.urlretrieve(url, file_path)
print(f'✅ Script downloaded to {file_path}')
print('Running script...')
subprocess.run(['python3', file_path])
PYEOF
```

---

## ⚙️ Configuration

**Script settings:**
- `MAX_INITIAL_SIZE_MB = 0.25` (250KB)
- `MIN_SEGMENT_SIZE_KB = 25.0` (25KB)

**This means:**
- Files >250KB will be automatically split
- Very small segments = minimal memory usage
- Maximum safety against OOM errors

---

## 📊 Expected Behavior

**The script will:**
1. Find all files >250KB
2. Split them into small segments (25KB minimum)
3. Process segments one at a time
4. Avoid memory issues completely

**Example:**
```
Scanning for files larger than 0.25MB...
  Found large file: filename1.txt (15.2MB)
  Found large file: filename2.txt (3.5MB)
  Found large file: filename3.txt (1.2MB)
  Found large file: filename4.txt (500KB)

Found 4 files larger than 0.25MB
```

**All files >250KB will be split automatically.**

---

## ✅ Summary

**Just copy the command above, paste into Render Shell, and press Enter!**

**The script will download and run automatically with 0.25MB threshold.**

