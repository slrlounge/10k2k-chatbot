# Quick Setup Guide

Follow these steps to get your RAG chatbot up and running:

## Step 1: Install Dependencies

```bash
source venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp env.example .env
# Edit .env and add your values
```

Required values:
- `GEMINI_API_KEY` - Get from [Google AI Studio](https://aistudio.google.com/)
- `GEMINI_STORE_ID` - Run `create_store.py` to get this

## Step 3: Create File Search Store

```bash
python create_store.py
```

Copy the Store ID and add it to `.env` as `GEMINI_STORE_ID`.

## Step 4: Upload Files to Store

You have two options:

### Option A: Via Google AI Studio (Recommended)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Navigate to File Search
3. Select your store
4. Upload files or connect GCS bucket

### Option B: Via Script
```bash
python upload_files_to_store.py gs://your-bucket/file1.pdf gs://your-bucket/file2.pdf
```

## Step 5: Create Test Token

```bash
python token_manager.py create test@example.com
```

Save the token - you'll need it to test the chatbot.

## Step 6: Run the Application

```bash
python app.py
```

Visit `http://localhost:8000` and enter your token to start chatting!

## Step 7: Integrate with Kajabi

### Quick Integration (Manual)
1. Create tokens for each customer: `python token_manager.py create customer@email.com`
2. Send tokens via Kajabi email automation
3. Customers enter token in chatbot

### Advanced Integration (Webhook)
1. Deploy `kajabi_webhook.py` to your server
2. Configure Kajabi webhook to point to your webhook endpoint
3. Tokens are automatically created/revoked based on purchases

## Testing the API

```bash
# Health check
curl http://localhost:8000/api/health

# Chat (replace YOUR_TOKEN with actual token)
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is this about?"}'
```

## Next Steps

- Customize the UI in `app.py` (search for "chat-container")
- Set up production deployment
- Configure CORS for your Kajabi domain
- Add rate limiting for production
- Set up monitoring and logging

For detailed documentation, see `README.md`.

