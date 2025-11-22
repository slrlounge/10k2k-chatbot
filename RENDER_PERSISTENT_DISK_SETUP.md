# Render Persistent Disk Setup for ChromaDB

## ⚠️ CRITICAL: Your ChromaDB data is being wiped on every deploy/restart!

ChromaDB stores all vector embeddings and metadata on the filesystem. Render's default filesystem is **ephemeral** - it gets wiped on every deploy or restart. You **MUST** add a persistent disk to prevent data loss.

---

## Step-by-Step: Add Persistent Disk to ChromaDB Service

### 1. Go to Your ChromaDB Service in Render Dashboard

1. Navigate to your Render dashboard
2. Click on your **`chromadb-w5jr`** service (or whatever your ChromaDB service is named)

### 2. Add Persistent Disk

1. In the service settings, scroll down to **"Disks"** section
2. Click **"Add Disk"**
3. Configure:
   - **Name**: `chromadb-data` (or any name you prefer)
   - **Mount Path**: `/chroma/chroma` ⚠️ **This must match exactly!**
   - **Size**: Start with **10GB** (you can increase later if needed)
4. Click **"Add Disk"**

### 3. Verify Disk is Attached

After adding the disk:
- The disk should appear in the "Disks" section
- Status should show as "Attached"
- The mount path should be `/chroma/chroma`

### 4. Redeploy the Service

1. Go to the **"Manual Deploy"** section
2. Click **"Deploy latest commit"** (or trigger a new deploy)
3. Wait for deployment to complete

---

## How to Verify Persistence is Working

### Option 1: Check Disk Usage (in Render Shell)

```bash
# Connect to Render Shell for chromadb-w5jr service
df -h /chroma/chroma
ls -lah /chroma/chroma
```

You should see:
- Disk mounted at `/chroma/chroma`
- Files/directories created by ChromaDB

### Option 2: Ingest Data, Restart, Check Again

1. **Before restart**: Ingest some files and check document count:
   ```bash
   python3 ingestion/check_ingestion_status.py
   ```

2. **Restart the service** (in Render dashboard, click "Restart")

3. **After restart**: Check document count again:
   ```bash
   python3 ingestion/check_ingestion_status.py
   ```

If persistence is working, the document count should be the same before and after restart.

---

## Troubleshooting

### Problem: Disk not showing up after adding

**Solution:**
- Make sure you clicked "Save" after adding the disk
- The service needs to be redeployed for the disk to be mounted
- Check that the mount path is exactly `/chroma/chroma` (no trailing slash)

### Problem: Data still being wiped

**Possible causes:**
1. **Wrong mount path**: Must be exactly `/chroma/chroma`
2. **Disk not attached**: Check "Disks" section shows the disk as "Attached"
3. **Service not redeployed**: Disk mount only happens during deployment

**Solution:**
- Verify mount path in Render dashboard matches `/chroma/chroma`
- Redeploy the service after adding the disk
- Check logs for any disk mounting errors

### Problem: "Disk full" errors

**Solution:**
- In Render dashboard, go to "Disks" section
- Click on your disk
- Increase the size (e.g., from 10GB to 20GB)
- Redeploy the service

---

## Cost Estimate

- **Persistent Disk**: ~$0.25/GB/month
- **10GB disk**: ~$2.50/month
- **20GB disk**: ~$5.00/month

Start with 10GB and increase if needed.

---

## Alternative: Use ChromaDB Cloud (Hosted)

If you prefer not to manage persistent disks, you can use **ChromaDB Cloud** (hosted service):

1. Sign up at https://www.trychroma.com/
2. Create a collection
3. Get your API key and endpoint URL
4. Update environment variables in `chatbot-api` and `ingest-chromadb`:
   - `CHROMA_URL=https://your-instance.chromadb.dev`
   - `CHROMA_API_KEY=your-api-key`

This eliminates the need for persistent disks but costs more (~$20-50/month).

---

## Summary

✅ **Required Steps:**
1. Add persistent disk to `chromadb-w5jr` service
2. Mount path: `/chroma/chroma`
3. Size: 10GB (minimum)
4. Redeploy service
5. Verify persistence works

⚠️ **Without a persistent disk, ALL your ingested data will be lost on every deploy/restart!**

