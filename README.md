# RAG Chatbot with Gemini FileSearch

A production-ready RAG (Retrieval-Augmented Generation) chatbot powered by Google's Gemini FileSearch API, designed to be integrated with Kajabi's paywall system using token-based authentication.

## Features

- 🤖 **Gemini FileSearch Integration**: Uses Google's Gemini FileSearch for intelligent document retrieval
- 🔐 **Token Authentication**: Secure token-based access control
- 🎨 **Modern UI**: Beautiful, responsive chatbot interface
- 🔗 **Kajabi Integration**: Webhook support for automatic token management
- 📝 **Conversation History**: Maintains context across chat sessions
- 🚀 **FastAPI Backend**: High-performance async API

## Prerequisites

- Python 3.9+
- Google Cloud Storage bucket with your files uploaded
- Gemini API enabled and API key
- File Search Store created (use `create_store.py`)

## Setup Instructions

### 1. Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install required packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp env.example .env
```

Edit `.env` and set the following:

```env
# Required: Your Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Required: Your File Search Store ID (from create_store.py)
GEMINI_STORE_ID=your_file_search_store_id_here

# Optional: Model to use (default: gemini-2.0-flash-exp)
GEMINI_MODEL=gemini-2.0-flash-exp

# Optional: Secret key for additional security
SECRET_KEY=your_secret_key_here

# Optional: Server configuration
HOST=0.0.0.0
PORT=8000
```

### 3. Create File Search Store (if not done already)

```bash
python create_store.py
```

Copy the Store ID that's printed and add it to your `.env` file as `GEMINI_STORE_ID`.

### 4. Upload Files to Your Store

You'll need to upload files from your Google Cloud Storage bucket to the File Search Store. You can do this via:

- Google AI Studio UI
- Or use the Gemini API to upload files programmatically

### 5. Create Access Tokens

Use the token manager to create tokens for your users:

```bash
# Create a token for a user (expires in 30 days by default)
python token_manager.py create user@example.com

# Create a token with custom expiration
python token_manager.py create user@example.com 90

# List all tokens
python token_manager.py list

# Revoke a token
python token_manager.py revoke <token>
```

### 6. Run the Application

```bash
python app.py
```

Or using uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The chatbot will be available at `http://localhost:8000`

## API Endpoints

### Chat Endpoint
- **POST** `/api/chat`
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  {
    "message": "Your question here",
    "conversation_history": [
      {"role": "user", "content": "Previous message"},
      {"role": "assistant", "content": "Previous response"}
    ]
  }
  ```
- **Response**:
  ```json
  {
    "response": "AI response text",
    "sources": [
      {"file_uri": "...", "chunk_index": 0}
    ]
  }
  ```

### Token Management
- **POST** `/api/tokens` - Create a new token (admin only)
- **GET** `/api/tokens` - List all tokens (admin only)

### Health Check
- **GET** `/api/health` - Check API health and configuration

## Kajabi Integration

### Option 1: Manual Token Distribution

1. Create tokens for each paying customer using `token_manager.py`
2. Distribute tokens through Kajabi's email automation or custom fields
3. Users enter their token in the chatbot interface

### Option 2: Webhook Integration (Recommended)

1. Set up the webhook handler:
   ```bash
   python kajabi_webhook.py
   ```

2. Configure Kajabi webhook:
   - Go to Kajabi Settings → Integrations → Webhooks
   - Create a new webhook pointing to: `https://your-domain.com/webhook/kajabi`
   - Set webhook secret in `.env` as `KAJABI_WEBHOOK_SECRET`
   - Subscribe to events:
     - `purchase.created` or `order.completed`
     - `purchase.cancelled` or `subscription.cancelled`
     - `purchase.refunded`

3. The webhook will automatically:
   - Create tokens when users purchase
   - Revoke tokens when users cancel or get refunded

### Option 3: Embed in Kajabi Site

You can embed the chatbot directly in your Kajabi site:

1. Add a custom HTML block in Kajabi
2. Include the chatbot interface (modify the HTML in `app.py` or create a separate frontend)
3. Use Kajabi's Liquid variables to pass user information

Example Kajabi integration snippet:
```html
<script>
  // Get user info from Kajabi
  const userId = "{{ customer.id }}";
  const userEmail = "{{ customer.email }}";
  
  // Make API call to get/create token
  fetch('/api/tokens', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_id: userId})
  })
  .then(res => res.json())
  .then(data => {
    // Set token in chatbot
    localStorage.setItem('chatbot_token', data.token);
  });
</script>
```

## Frontend Customization

The chatbot UI is embedded in `app.py`. To customize:

1. Modify the HTML/CSS/JavaScript in the `root()` endpoint
2. Or create a separate frontend application that calls `/api/chat`
3. Update CORS settings in `app.py` to allow your domain

## Production Deployment

### Security Checklist

- [ ] Set `SECRET_KEY` to a strong random value
- [ ] Configure CORS to only allow your Kajabi domain
- [ ] Use HTTPS for all API calls
- [ ] Implement rate limiting
- [ ] Use a database instead of JSON file for tokens
- [ ] Set up proper logging and monitoring
- [ ] Configure firewall rules
- [ ] Use environment variables for all secrets

### Recommended Hosting Options

- **Google Cloud Run**: Serverless, auto-scaling
- **AWS Lambda + API Gateway**: Serverless
- **DigitalOcean App Platform**: Simple deployment
- **Heroku**: Easy deployment
- **Railway**: Modern platform

### Environment Variables for Production

Make sure to set these in your hosting platform:

```env
GEMINI_API_KEY=your_key
GEMINI_STORE_ID=your_store_id
SECRET_KEY=strong_random_key
KAJABI_WEBHOOK_SECRET=your_webhook_secret
```

## Troubleshooting

### "Gemini client not initialized"
- Check that `GEMINI_API_KEY` is set correctly
- Verify the API key is valid in Google AI Studio

### "GEMINI_STORE_ID not configured"
- Run `create_store.py` to create a store
- Copy the Store ID to your `.env` file

### "Invalid or expired token"
- Verify the token exists: `python token_manager.py list`
- Check if token was revoked
- Ensure token hasn't expired

### Files not being found
- Verify files are uploaded to the File Search Store
- Check file permissions in Google Cloud Storage
- Ensure the store ID matches your store

## File Structure

```
.
├── app.py                 # Main FastAPI application
├── create_store.py        # Script to create File Search Store
├── token_manager.py       # Token management utility
├── kajabi_webhook.py      # Kajabi webhook handler
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── tokens.json           # Token storage (created automatically)
└── README.md             # This file
```

## Next Steps

1. ✅ Set up your environment variables
2. ✅ Create your File Search Store
3. ✅ Upload files to the store
4. ✅ Create tokens for test users
5. ✅ Test the chatbot locally
6. ✅ Deploy to production
7. ✅ Configure Kajabi integration
8. ✅ Set up monitoring and logging

## Support

For issues related to:
- **Gemini API**: Check [Google AI Studio](https://aistudio.google.com/)
- **FileSearch**: See [Gemini FileSearch Documentation](https://ai.google.dev/gemini-api/docs/file-search)
- **Kajabi**: Check [Kajabi Webhooks Documentation](https://help.kajabi.com/)

## License

This project is provided as-is for your use case.

