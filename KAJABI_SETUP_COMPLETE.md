# 🚀 Complete Kajabi Integration Guide - Step by Step

Your chatbot is **LIVE** at: `https://chatbot-api-odio.onrender.com`

---

## ✅ Pre-Flight Checklist

Before embedding, verify these are set in Render:

### Environment Variables (chatbot-api → Environment)
- [ ] `ENABLE_AUTH=true`
- [ ] `AUTH_SECRET_KEY` = (your secret key - keep this secure!)
- [ ] `KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login`
- [ ] `TOKEN_EXPIRATION_MINUTES=1440` (24 hours, or adjust as needed)
- [ ] `ALLOWED_ORIGINS=https://www.slrloungeworkshops.com,https://slrloungeworkshops.com`

---

## 📋 Step-by-Step: Embed in Kajabi

### STEP 1: Generate Tokens for Your Members

You have **3 options** for token generation:

#### Option A: Pre-Generate Tokens (Simplest - Recommended for Testing)

**Run this locally to generate tokens:**

```bash
cd /Users/justinlin/Documents/10K2KChatBot
source .venv/bin/activate
python3 << 'EOF'
from auth.token_utils import generate_token
import os
from dotenv import load_dotenv

load_dotenv()

# Replace with actual Kajabi user IDs
user_ids = [
    "kajabi_user_12345",  # Example user ID
    "kajabi_user_67890",  # Another user ID
]

print("\n" + "="*70)
print("🔑 GENERATING TOKENS FOR KAJABI MEMBERS")
print("="*70)
print()

for user_id in user_ids:
    token = generate_token(user_id, expiration_minutes=1440)  # 24 hours
    url = f"https://chatbot-api-odio.onrender.com/web/chat.html?token={token}"
    print(f"User ID: {user_id}")
    print(f"Token: {token}")
    print(f"URL: {url}")
    print("-" * 70)
    print()
EOF
```

**Save the tokens** - you'll use them in Kajabi.

#### Option B: Use API Endpoint (Dynamic - Recommended for Production)

Your API already has a token generation endpoint:

**Endpoint:** `POST https://chatbot-api-odio.onrender.com/auth/generate-token`

**Request:**
```json
{
  "user_id": "kajabi_user_12345",
  "secret_key": "YOUR_ADMIN_SECRET_KEY"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "kajabi_user_12345"
}
```

**Test it:**
```bash
curl -X POST "https://chatbot-api-odio.onrender.com/auth/generate-token?user_id=test_user&secret_key=YOUR_ADMIN_SECRET_KEY"
```

#### Option C: Use Kajabi Webhooks (Most Automated)

1. **Set up Kajabi webhook** that triggers when a member accesses a lesson
2. **Webhook calls your endpoint:** `POST /auth/generate-token`
3. **Your API generates token** and returns it
4. **Kajabi embeds chatbot** with token in URL

---

### STEP 2: Update Frontend API URL (If Needed)

The frontend is already configured, but verify:

**File:** `web/chat.html` (line ~1279)

```javascript
const API_URL = window.API_URL || 'https://chatbot-api-odio.onrender.com';
```

✅ This is already set correctly!

---

### STEP 3: Embed in Kajabi Lesson

#### Method 1: Simple Iframe Embed (Easiest)

**In Kajabi Lesson Editor:**

1. Click **"Add Block"** → **"Custom Code"** or **"HTML Block"**
2. Paste this code:

```html
<div id="chatbot-container" style="width: 100%; height: 800px; margin: 20px 0;">
    <iframe 
        src="https://chatbot-api-odio.onrender.com/web/chat.html?token=YOUR_TOKEN_HERE" 
        width="100%" 
        height="100%"
        frameborder="0"
        style="border: none; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
        allow="clipboard-read; clipboard-write">
    </iframe>
</div>
```

**Replace `YOUR_TOKEN_HERE`** with the token from Step 1.

#### Method 2: Dynamic Token Generation (Advanced)

If you want tokens generated per user automatically:

```html
<div id="chatbot-container" style="width: 100%; height: 800px; margin: 20px 0;"></div>

<script>
(async function() {
    // Get Kajabi user ID (adjust based on Kajabi's available variables)
    // Common Kajabi variables: {{user.id}}, {{member.id}}, {{customer.id}}
    const userId = '{{user.id}}'; // Adjust this to match Kajabi's variable syntax
    
    // Your admin secret key (keep this secure - consider using Kajabi's secure storage)
    const adminSecret = 'YOUR_ADMIN_SECRET_KEY';
    
    try {
        // Generate token from your API
        const response = await fetch(
            `https://chatbot-api-odio.onrender.com/auth/generate-token?user_id=${userId}&secret_key=${adminSecret}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );
        
        if (!response.ok) {
            throw new Error('Failed to generate token');
        }
        
        const data = await response.json();
        
        // Create iframe with token
        const iframe = document.createElement('iframe');
        iframe.src = `https://chatbot-api-odio.onrender.com/web/chat.html?token=${data.token}`;
        iframe.width = '100%';
        iframe.height = '100%';
        iframe.frameBorder = '0';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        iframe.setAttribute('allow', 'clipboard-read; clipboard-write');
        
        document.getElementById('chatbot-container').appendChild(iframe);
    } catch (error) {
        console.error('Error loading chatbot:', error);
        document.getElementById('chatbot-container').innerHTML = 
            '<div style="padding: 40px; text-align: center; color: #666;">' +
            '<p>Unable to load chatbot. Please refresh the page or contact support.</p>' +
            '</div>';
    }
})();
</script>
```

**Note:** Kajabi may have restrictions on JavaScript execution. If this doesn't work, use Method 1 with pre-generated tokens.

#### Method 3: Direct Link Button

Create a button that opens the chatbot in a new tab:

```html
<a href="https://chatbot-api-odio.onrender.com/web/chat.html?token=YOUR_TOKEN_HERE" 
   target="_blank"
   style="display: inline-block; padding: 16px 32px; background: #2c3e50; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-family: 'Montserrat', sans-serif; margin: 20px 0;">
    💬 Chat with Your AI Mentor
</a>
```

---

### STEP 4: Test the Integration

1. **Test without token first** (if auth is disabled):
   - Set `ENABLE_AUTH=false` temporarily
   - Embed iframe without token
   - Verify chatbot loads

2. **Test with token**:
   - Set `ENABLE_AUTH=true`
   - Generate a test token
   - Embed with token in URL
   - Verify chatbot loads and works

3. **Test token expiration**:
   - Generate token with short expiration (1 minute)
   - Wait for expiration
   - Verify redirect to Kajabi login

4. **Test from Kajabi**:
   - Access the lesson as a member
   - Verify chatbot loads
   - Test asking a question
   - Verify responses work

---

## 🔒 Security Best Practices

### 1. Protect Your Admin Secret Key

**DO NOT** hardcode `ADMIN_SECRET_KEY` in Kajabi custom code blocks!

**Instead:**
- Use Kajabi's secure storage (if available)
- Or use server-side token generation via webhooks
- Or pre-generate tokens server-side and store securely

### 2. Token Expiration

- **Default:** 24 hours (1440 minutes)
- **Adjust:** Set `TOKEN_EXPIRATION_MINUTES` in environment variables
- **Recommendation:** 24-168 hours (1-7 days) for good UX

### 3. CORS Configuration

Your `ALLOWED_ORIGINS` should include:
- `https://www.slrloungeworkshops.com`
- `https://slrloungeworkshops.com` (without www)
- Any other Kajabi domains you use

---

## 🐛 Troubleshooting

### Chatbot doesn't load

**Check:**
1. Is `ENABLE_AUTH=true` and token is valid?
2. Check browser console (F12) for errors
3. Verify chatbot URL is correct: `https://chatbot-api-odio.onrender.com/web/chat.html`
4. Check CORS settings in Render environment variables

### "Authentication required" error

**Causes:**
- Token missing from URL
- Token expired
- `AUTH_SECRET_KEY` mismatch between token generation and validation

**Fix:**
- Regenerate token with correct `AUTH_SECRET_KEY`
- Check token expiration time
- Verify token is in URL: `?token=...`

### Iframe blocked or blank

**Causes:**
- CORS issues
- Content Security Policy (CSP) restrictions
- JavaScript errors

**Fix:**
- Check browser console for errors
- Verify `ALLOWED_ORIGINS` includes Kajabi domain
- Test iframe in a simple HTML page first

### API requests failing

**Check:**
1. Is Render service `Live`?
2. Check Render logs for errors
3. Verify `API_URL` in `chat.html` matches Render URL
4. Test API directly: `https://chatbot-api-odio.onrender.com/health`

---

## 📊 Monitoring

### Check Service Status

1. **Render Dashboard:**
   - Go to `chatbot-api` service
   - Verify status is `Live` (green)
   - Check logs for any errors

2. **Health Endpoint:**
   - Visit: `https://chatbot-api-odio.onrender.com/health`
   - Should return: `{"status": "healthy", ...}`

3. **Test Chat Endpoint:**
   - Use Postman or curl to test `/ask` endpoint
   - Verify responses work

---

## 🎯 Quick Start Summary

**For immediate testing:**

1. **Generate a test token:**
   ```bash
   python3 -c "from auth.token_utils import generate_token; print(generate_token('test_user', 1440))"
   ```

2. **Embed in Kajabi:**
   ```html
   <iframe src="https://chatbot-api-odio.onrender.com/web/chat.html?token=YOUR_TOKEN" width="100%" height="800px" frameborder="0"></iframe>
   ```

3. **Test it!**

---

## 📞 Next Steps

1. ✅ **Verify environment variables** in Render
2. ✅ **Generate tokens** for your members
3. ✅ **Embed in Kajabi** lesson
4. ✅ **Test thoroughly**
5. ✅ **Monitor logs** for any issues
6. ✅ **Gather user feedback**

---

## 🔗 Important URLs

- **Chatbot URL:** `https://chatbot-api-odio.onrender.com/web/chat.html`
- **API Health:** `https://chatbot-api-odio.onrender.com/health`
- **Token Generation:** `https://chatbot-api-odio.onrender.com/auth/generate-token`
- **Kajabi Login:** `https://www.slrloungeworkshops.com/login`

---

## 💡 Pro Tips

1. **Start with one test user** - Generate a token and test thoroughly before rolling out
2. **Use longer token expiration** for better UX (7 days is good)
3. **Monitor Render logs** regularly for any issues
4. **Set up alerts** in Render for service failures
5. **Test on mobile** - Your chatbot is responsive!

---

**Need help?** Check the logs in Render or review the troubleshooting section above.

