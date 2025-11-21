# 🔧 Updated: Much Smaller File Size Threshold

## ⚠️ Issue
Files need to be much smaller than 5MB to prevent OOM errors.

---

## ✅ Solution: Updated Script

**I've updated the script to use a 1MB threshold instead of 5MB.**

**New settings:**
- `MAX_INITIAL_SIZE_MB = 1.0` - Try files up to 1MB as-is
- `MIN_SEGMENT_SIZE_KB = 50.0` - Minimum 50KB per segment

**This means:**
- Files >1MB will be automatically split
- Much smaller segments = less memory usage
- Prevents OOM errors

---

## 🚀 Updated Command

**Run this updated command in Render Shell:**

```python
python3 << 'PYEOF'
import urllib.request
import subprocess
url = 'https://raw.githubusercontent.com/slrlounge/10k2k-chatbot/main/ingestion/ingest_with_recursive_splitting_standalone.py'
file_path = '/app/ingestion/ingest_with_recursive_splitting_standalone.py'
print("Downloading updated script (1MB threshold)...")
urllib.request.urlretrieve(url, file_path)
print(f"✅ Script downloaded to {file_path}")
print("Running script...")
subprocess.run(['python3', file_path])
PYEOF
```

---

## 📊 What Changed

### Before:
- Files up to 5MB tried as-is
- Files >5MB split
- Still causing OOM errors

### After:
- Files up to 1MB tried as-is
- Files >1MB automatically split
- Much smaller segments
- Prevents OOM errors

---

## 🎯 Expected Behavior

**Now the script will:**
1. Find all files >1MB (instead of >5MB)
2. Split them into smaller segments
3. Process segments one at a time
4. Avoid memory issues

**Example:**
```
Scanning for files larger than 1.0MB...
  Found large file: filename1.txt (15.2MB)
  Found large file: filename2.txt (3.5MB)
  Found large file: filename3.txt (2.1MB)

Found 3 files larger than 1.0MB
```

**All files >1MB will be split, not just >5MB.**

---

## ⚙️ Further Adjustments (If Needed)

**If 1MB is still too large, you can adjust:**

**In the script, change:**
```python
MAX_INITIAL_SIZE_MB = 0.5  # Even smaller: 500KB
```

**Or:**
```python
MAX_INITIAL_SIZE_MB = 0.25  # Very small: 250KB
```

**The smaller the threshold, the more files will be split, but the safer it is.**

---

## ✅ Summary

**Updated script:**
- ✅ Uses 1MB threshold (instead of 5MB)
- ✅ Automatically splits files >1MB
- ✅ Prevents OOM errors
- ✅ Pushed to GitHub

**Run the updated command above to download and run the new version!**

