# Fix Dockerfile Path in Render

## Problem
Render is building `ingest-chromadb` service with the wrong Dockerfile:
- ❌ Currently using: `Dockerfile` (includes Whisper, PyTorch, CUDA - 3GB+)
- ✅ Should use: `Dockerfile.ingest` (lightweight ingestion only - ~100MB)

## Evidence from Logs
```
#9 [ 4/10] COPY requirements.txt .          ← Wrong file!
#10 [ 5/10] RUN pip install ...             ← Installing Whisper, PyTorch, etc.
```

## Solution Steps

### Step 1: Cancel Current Deployment
1. Go to Render Dashboard: https://dashboard.render.com
2. Navigate to your `ingest-chromadb` service
3. Click **"Cancel"** or **"Stop"** on the current deployment
4. Wait for it to stop (may take 1-2 minutes)

### Step 2: Fix Dockerfile Path
1. In the `ingest-chromadb` service page, click **"Settings"** tab
2. Scroll down to **"Docker"** section
3. Find **"Dockerfile Path"** field
4. Change from: `Dockerfile`
5. Change to: `Dockerfile.ingest`
6. Click **"Save Changes"**

### Step 3: Redeploy
1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Or push a new commit to trigger auto-deploy

## Expected Results

### Before Fix (Current)
- Build time: 10-15 minutes
- Image size: ~3-4GB
- Installs: PyTorch, CUDA, Whisper, FFmpeg
- Memory usage: High

### After Fix
- Build time: 2-3 minutes
- Image size: ~200-300MB
- Installs: Only ChromaDB, LangChain, OpenAI (lightweight)
- Memory usage: Low

## Verification
After redeploy, check logs. You should see:
```
#9 [ 4/10] COPY requirements.ingest.txt .     ← Correct file!
#10 [ 5/10] RUN pip install ...              ← Only lightweight packages
```

## If You Can't Find the Setting
1. Make sure you're in the **Settings** tab (not Environment or Logs)
2. Look for "Docker" or "Build" section
3. The field might be labeled "Dockerfile" or "Dockerfile Path"
4. If still not found, Render may have moved it - check their docs or support

