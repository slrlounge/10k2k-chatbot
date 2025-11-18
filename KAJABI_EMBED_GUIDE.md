# How to Embed the Chatbot in Kajabi

This guide shows you exactly how to embed the chatbot in your Kajabi course pages.

## Option 1: Iframe Embedding (Recommended)

### Step 1: Get Your Chatbot URL

Your chatbot URL should be:
```
https://your-chatbot-domain.com/web/chat.html
```

Or if using ngrok:
```
https://your-ngrok-url.ngrok-free.dev/web/chat.html
```

### Step 2: Generate a Token for the User

You need to generate a token that includes the user's Kajabi ID. There are two ways to do this:

#### Method A: Use Kajabi Webhooks (Recommended)

1. **Set up a Kajabi webhook** that triggers when a user accesses a lesson
2. **Create a token generation endpoint** in your chatbot (see below)
3. **Kajabi calls your endpoint** → You generate token → Return to Kajabi → Embed in iframe

#### Method B: Use Kajabi Custom Code Block

If Kajabi allows custom code blocks, you can generate tokens directly:

```html
<script>
// This would need to run server-side or via API call
// See "Token Generation Endpoint" section below
</script>
```

### Step 3: Embed in Kajabi Lesson

In your Kajabi lesson editor, add a **Custom Code Block** or **HTML Block**:

```html
<iframe 
    src="https://your-chatbot-domain.com/web/chat.html?token=TOKEN_HERE" 
    width="100%" 
    height="800px"
    frameborder="0"
    style="border: none; border-radius: 8px;"
    allow="clipboard-read; clipboard-write">
</iframe>
```

**Replace `TOKEN_HERE`** with the actual token generated for the user.

## Option 2: Direct Link Button

Create a button that links directly to the chatbot:

```html
<a href="https://your-chatbot-domain.com/web/chat.html?token=TOKEN_HERE" 
   target="_blank"
   style="display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">
    Open AI Mentor Chatbot
</a>
```

## Token Generation Options

### Option A: Server-Side Token Generation Endpoint

Add this endpoint to your `serve.py` to generate tokens server-side:

```python
@app.post("/auth/generate-token")
async def generate_token_for_user(
    user_id: str,
    secret_key: str = Query(None)  # Optional: require admin secret
):
    """
    Generate a token for a Kajabi user.
    
    This endpoint can be called by Kajabi webhooks or custom code.
    """
    from auth.token_utils import generate_token
    
    # Optional: Verify admin secret key
    ADMIN_SECRET = os.getenv('ADMIN_SECRET_KEY', '')
    if ADMIN_SECRET and secret_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    token = generate_token(user_id)
    return {"token": token, "user_id": user_id}
```

**Usage from Kajabi:**
```javascript
// In Kajabi custom code block
fetch('https://your-chatbot-domain.com/auth/generate-token?user_id={{kajabi_user_id}}&secret_key=YOUR_ADMIN_SECRET', {
    method: 'POST'
})
.then(response => response.json())
.then(data => {
    const iframe = document.createElement('iframe');
    iframe.src = `https://your-chatbot-domain.com/web/chat.html?token=${data.token}`;
    iframe.width = '100%';
    iframe.height = '800px';
    iframe.frameBorder = '0';
    document.getElementById('chatbot-container').appendChild(iframe);
});
```

### Option B: Pre-Generate Tokens (Simpler)

If you know the user IDs, you can pre-generate tokens:

```python
from auth.token_utils import generate_token

# Generate token for a specific user
user_id = "kajabi_user_12345"
token = generate_token(user_id, expiration_minutes=60*24*7)  # 7 days

print(f"Token: {token}")
print(f"URL: https://your-chatbot-domain.com/web/chat.html?token={token}")
```

Then manually add the token to your Kajabi lesson HTML.

## Quick Start: Simple Embed (No Auth)

If you want to test without authentication first:

1. **Set `ENABLE_AUTH=false` in your `.env`**
2. **Embed directly:**

```html
<iframe 
    src="https://your-chatbot-domain.com/web/chat.html" 
    width="100%" 
    height="800px"
    frameborder="0"
    style="border: none;">
</iframe>
```

## Step-by-Step: Full Setup with Authentication

### 1. Configure Environment Variables

Make sure your `.env` has:
```bash
ENABLE_AUTH=true
AUTH_SECRET_KEY=your_secret_key_here
KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
TOKEN_EXPIRATION_MINUTES=1440  # 24 hours
```

### 2. Generate Tokens for Users

**Option 1: Use Python script**
```python
from auth.token_utils import generate_token

# For a specific user
user_id = "kajabi_user_12345"
token = generate_token(user_id, expiration_minutes=1440)
print(f"Token: {token}")
```

**Option 2: Use API endpoint** (if you add the `/auth/generate-token` endpoint)

### 3. Embed in Kajabi

**In Kajabi Lesson Editor:**

1. Click **"Add Block"** → **"Custom Code"** or **"HTML"**
2. Paste this code:

```html
<div id="chatbot-container" style="width: 100%; height: 800px; margin: 20px 0;">
    <iframe 
        src="https://your-chatbot-domain.com/web/chat.html?token=YOUR_TOKEN_HERE" 
        width="100%" 
        height="100%"
        frameborder="0"
        style="border: none; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
        allow="clipboard-read; clipboard-write">
    </iframe>
</div>
```

**Replace:**
- `your-chatbot-domain.com` with your actual domain
- `YOUR_TOKEN_HERE` with the generated token

### 4. Dynamic Token Generation (Advanced)

If you want tokens generated dynamically per user, you'll need:

1. **Kajabi Webhook** that calls your token generation endpoint
2. **Custom JavaScript** in Kajabi that fetches token and embeds iframe

**Example Kajabi Custom Code:**

```html
<div id="chatbot-container"></div>

<script>
(async function() {
    // Get Kajabi user ID (adjust based on Kajabi's API)
    const userId = '{{kajabi_user_id}}'; // Kajabi variable
    
    try {
        // Generate token
        const response = await fetch('https://your-chatbot-domain.com/auth/generate-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: userId })
        });
        
        const data = await response.json();
        
        // Create iframe with token
        const iframe = document.createElement('iframe');
        iframe.src = `https://your-chatbot-domain.com/web/chat.html?token=${data.token}`;
        iframe.width = '100%';
        iframe.height = '800px';
        iframe.frameBorder = '0';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        
        document.getElementById('chatbot-container').appendChild(iframe);
    } catch (error) {
        console.error('Error loading chatbot:', error);
        document.getElementById('chatbot-container').innerHTML = 
            '<p>Error loading chatbot. Please refresh the page.</p>';
    }
})();
</script>
```

## Testing

1. **Test without auth first:**
   - Set `ENABLE_AUTH=false`
   - Embed iframe directly
   - Verify chatbot loads

2. **Test with auth:**
   - Set `ENABLE_AUTH=true`
   - Generate a test token
   - Embed with token in URL
   - Verify chatbot loads

3. **Test token expiration:**
   - Generate token with short expiration (1 minute)
   - Wait for expiration
   - Verify redirect to Kajabi login

## Troubleshooting

### Chatbot doesn't load
- Check if `ENABLE_AUTH=true` and token is valid
- Check browser console for errors
- Verify chatbot URL is correct
- Check CORS settings if loading from different domain

### "Authentication required" error
- Token missing from URL
- Token expired
- `AUTH_SECRET_KEY` mismatch

### Iframe blocked
- Check iframe `allow` attributes
- Verify CORS headers on chatbot server
- Check browser console for security errors

## Next Steps

1. **Choose your embedding method** (iframe or direct link)
2. **Set up token generation** (pre-generate or dynamic)
3. **Add to Kajabi lesson** using Custom Code block
4. **Test with a real user**
5. **Monitor logs** for any auth issues

