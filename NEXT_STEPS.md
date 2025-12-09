# Next Steps - Quick Guide

You have:
- ✅ API Key from Google AI Studio
- ✅ 96 files uploaded to GCS bucket `slr-rag-gemini`

## Step-by-Step Setup

### Step 1: Configure Environment Variables

Create `.env` file:

```bash
cp env.example .env
```

Edit `.env` and add your API key:

```env
GEMINI_API_KEY=AlzaSyA68m_MJ0aOXfhw03mH8nRwd5WFmx47a-Q
GEMINI_STORE_ID=  # We'll get this in next step
GEMINI_MODEL=gemini-2.0-flash-exp
```

**⚠️ Important:** Replace the API key above with your actual key from Google AI Studio.

### Step 2: Create File Search Store

```bash
python create_store.py
```

This will:
- Create a File Search Store named "Kajabi_Knowledge_Base"
- Print the Store ID
- **Copy the Store ID** and add it to `.env` as `GEMINI_STORE_ID`

### Step 3: Upload Files to File Search Store

You have **two options**:

#### Option A: Via Google AI Studio (Easiest - Recommended)

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Navigate to **File Search** section (left sidebar)
3. Click on your store: **Kajabi_Knowledge_Base**
4. Click **"Add files"** or **"Connect GCS bucket"**
5. Select your bucket: `gs://slr-rag-gemini`
6. Wait for files to be indexed (may take a few minutes)

#### Option B: Via Script (Programmatic)

If you have `gsutil` installed:

```bash
python upload_gcs_to_store.py
```

This will upload all 96 files from your GCS bucket to the File Search Store.

**Note:** You need Google Cloud SDK installed for this option:
```bash
# Install gcloud CLI if needed
# macOS: brew install google-cloud-sdk
```

### Step 4: Test Your Chatbot

1. **Start the server:**
   ```bash
   python app.py
   ```

2. **Create a test token:**
   ```bash
   python token_manager.py create test@example.com
   ```
   Copy the token that's printed.

3. **Open in browser:**
   - Go to `http://localhost:8000`
   - Paste your token
   - Click "Set Token"
   - Start chatting!

4. **Or test via API:**
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "What topics are covered in your knowledge base?", "conversation_history": []}'
   ```

## Quick Setup Script

Run this to automate steps 1-3:

```bash
python setup_next_steps.py
```

This script will:
- ✅ Check your `.env` configuration
- ✅ Create File Search Store if needed
- ✅ Guide you through uploading files
- ✅ Provide testing instructions

## Troubleshooting

### "GEMINI_API_KEY not set"
- Make sure `.env` file exists
- Check that API key is correct (no extra spaces)

### "Store ID not found"
- Run `python create_store.py` first
- Copy the Store ID to `.env`

### "Files not found in chatbot responses"
- Make sure files are uploaded to File Search Store (not just GCS)
- Wait a few minutes for indexing to complete
- Check in Google AI Studio that files show up in your store

### "gsutil not found"
- Install Google Cloud SDK
- Or use Option A (Google AI Studio UI) instead

## What's Next?

Once testing works:

1. ✅ Customize the chatbot UI (edit HTML in `app.py`)
2. ✅ Set up production deployment
3. ✅ Configure Kajabi integration
4. ✅ Create tokens for your customers
5. ✅ Deploy and go live!

## Need Help?

- Check `README.md` for detailed documentation
- Review `SETUP_GUIDE.md` for setup instructions
- Check server logs if something doesn't work


